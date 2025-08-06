"""
Pure Python implementation of s3quilt functionality.

This module provides parallel S3 object chunk downloading capabilities
without requiring Go dependencies.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple, Union
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from botocore import UNSIGNED


class S3ChunkDownloader:
    """Handles parallel downloading of S3 object chunks."""
    
    def __init__(self, bucket: str, key: str, concurrency: int = 50):
        """
        Initialize the S3 chunk downloader.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            concurrency: Number of concurrent downloads (default: 50)
        """
        self.bucket = bucket
        self.key = key
        self.concurrency = concurrency
        self.region = None
        self.anonymous = False
        self._client = None
        
    def _get_s3_client(self) -> boto3.client:
        """Get or create S3 client with proper configuration."""
        if self._client is not None:
            return self._client
            
        # Try to detect region and credentials
        try:
            # First, try with default credentials to detect region
            temp_client = boto3.client('s3', region_name='us-west-2')
            temp_client.head_bucket(Bucket=self.bucket)
            self.region = temp_client.get_bucket_location(Bucket=self.bucket)['LocationConstraint']
            if self.region is None:
                self.region = 'us-east-1'  # Default for us-east-1
        except (ClientError, NoCredentialsError) as e:
            if 'credentials' in str(e).lower() or 'unable to locate credentials' in str(e).lower():
                self.anonymous = True
                self.region = 'us-west-2'  # Default region for anonymous access
            else:
                # Try to get region anyway
                try:
                    temp_client = boto3.client('s3', 
                                             region_name='us-west-2',
                                             config=Config(signature_version=UNSIGNED))
                    self.region = temp_client.get_bucket_location(Bucket=self.bucket)['LocationConstraint']
                    if self.region is None:
                        self.region = 'us-east-1'
                    self.anonymous = True
                except Exception:
                    self.region = 'us-west-2'
                    self.anonymous = True
        
        # Create the final client with proper configuration
        if self.anonymous:
            self._client = boto3.client('s3',
                                      region_name=self.region,
                                      config=Config(signature_version=UNSIGNED))
        else:
            self._client = boto3.client('s3', region_name=self.region)
            
        return self._client
    
    def _download_chunk(self, start: int, length: int, idx: int) -> Tuple[int, Union[str, bytes]]:
        """
        Download a single chunk from S3.
        
        Args:
            start: Starting byte position in S3 object
            length: Number of bytes to download
            idx: Index of this chunk for ordering
            
        Returns:
            Tuple of (index, chunk_data)
        """
        client = self._get_s3_client()
        range_header = f'bytes={start}-{start + length - 1}'
        
        response = client.get_object(
            Bucket=self.bucket,
            Key=self.key,
            Range=range_header
        )
        
        chunk_data = response['Body'].read()
        return idx, chunk_data.decode('utf-8', errors='replace')
    
    def _write_chunk_to_file(self, start: int, length: int, local_offset: int, 
                           output_file_handle) -> None:
        """
        Download a chunk and write it directly to a file at the specified offset.
        
        Args:
            start: Starting byte position in S3 object
            length: Number of bytes to download
            local_offset: Offset in the local file to write to
            output_file_handle: File handle to write to
        """
        client = self._get_s3_client()
        range_header = f'bytes={start}-{start + length - 1}'
        
        response = client.get_object(
            Bucket=self.bucket,
            Key=self.key,
            Range=range_header
        )
        
        chunk_data = response['Body'].read()
        
        # Thread-safe file writing at specific offset
        with threading.Lock():
            output_file_handle.seek(local_offset)
            output_file_handle.write(chunk_data)
    
    def download_chunks(self, starts: List[int], lengths: List[int]) -> List[str]:
        """
        Download multiple chunks from S3 object in parallel.
        
        Args:
            starts: List of starting byte positions
            lengths: List of chunk lengths (must match starts length)
            
        Returns:
            List of chunk data as strings, ordered by input order
            
        Raises:
            ValueError: If starts and lengths lists have different lengths
            Exception: If any download fails
        """
        if len(starts) != len(lengths):
            raise ValueError("starts and lengths must have the same length")
        
        results = [None] * len(starts)
        
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            # Submit all download tasks
            future_to_idx = {
                executor.submit(self._download_chunk, starts[i], lengths[i], i): i
                for i in range(len(starts))
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_idx):
                try:
                    idx, chunk_data = future.result()
                    results[idx] = chunk_data
                except Exception as e:
                    raise Exception(f"Failed to download chunk: {e}") from e
        
        return results
    
    def download_chunks_to_file(self, output_file_path: str, starts: List[int], 
                              lengths: List[int]) -> None:
        """
        Download multiple chunks from S3 object and write them to a file.
        
        Args:
            output_file_path: Path to output file
            starts: List of starting byte positions
            lengths: List of chunk lengths (must match starts length)
            
        Raises:
            ValueError: If starts and lengths lists have different lengths
            Exception: If any download fails
        """
        if len(starts) != len(lengths):
            raise ValueError("starts and lengths must have the same length")
        
        # Calculate total file size and create file
        total_size = sum(lengths)
        
        with open(output_file_path, 'wb') as output_file:
            # Pre-allocate file space
            output_file.seek(total_size - 1)
            output_file.write(b'\0')
            output_file.seek(0)
            
            with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                # Calculate local offsets
                local_offset = 0
                futures = []
                
                for i in range(len(starts)):
                    future = executor.submit(
                        self._write_chunk_to_file, 
                        starts[i], 
                        lengths[i], 
                        local_offset,
                        output_file
                    )
                    futures.append(future)
                    local_offset += lengths[i]
                
                # Wait for all downloads to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        raise Exception(f"Failed to download chunk to file: {e}") from e


def download_chunks(bucket: str, key: str, starts: List[int], 
                   lengths: List[int], concurrency: int = 50) -> List[str]:
    """
    Download multiple chunks from an S3 object in parallel.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        starts: List of starting byte positions
        lengths: List of chunk lengths
        concurrency: Number of concurrent downloads (default: 50)
        
    Returns:
        List of chunk data as strings
    """
    downloader = S3ChunkDownloader(bucket, key, concurrency)
    return downloader.download_chunks(starts, lengths)


def download_chunks_to_file(bucket: str, key: str, output_file_path: str,
                          starts: List[int], lengths: List[int], 
                          concurrency: int = 50) -> None:
    """
    Download multiple chunks from an S3 object and save to a file.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        output_file_path: Path to output file
        starts: List of starting byte positions
        lengths: List of chunk lengths
        concurrency: Number of concurrent downloads (default: 50)
    """
    downloader = S3ChunkDownloader(bucket, key, concurrency)
    downloader.download_chunks_to_file(output_file_path, starts, lengths)