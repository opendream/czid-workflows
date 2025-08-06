from typing import Iterable, List

from .s3quilt_pure import download_chunks as _download_chunks
from .s3quilt_pure import download_chunks_to_file as _download_chunks_to_file

"""
Pure Python implementation of S3 chunk downloading.
The process is mostly IO bound so high concurrency is beneficial.
"""


def download_chunks(
    bucket: str,
    key: str,
    starts: Iterable[int],
    lengths: Iterable[int],
    concurrency: int = 100,
) -> List[str]:
    """
    Download multiple chunks from an S3 object in parallel.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        starts: Iterable of starting byte positions
        lengths: Iterable of chunk lengths
        concurrency: Number of concurrent downloads (default: 100)
        
    Returns:
        List of chunk data as strings
    """
    return _download_chunks(bucket, key, list(starts), list(lengths), concurrency)


def download_chunks_to_file(
    bucket: str,
    key: str,
    filepath: str,
    starts: Iterable[int],
    lengths: Iterable[int],
    concurrency: int = 100,
) -> None:
    """
    Download multiple chunks from an S3 object and save to a file.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        filepath: Path to output file
        starts: Iterable of starting byte positions
        lengths: Iterable of chunk lengths
        concurrency: Number of concurrent downloads (default: 100)
    """
    _download_chunks_to_file(bucket, key, filepath, list(starts), list(lengths), concurrency)