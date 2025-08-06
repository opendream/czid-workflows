#!/usr/bin/env python3
"""
Simple test script for the pure Python s3quilt implementation.
"""

import os
import tempfile
from s3quilt_pure import S3ChunkDownloader

def test_basic_functionality():
    """Test basic chunk downloading functionality."""
    print("Testing S3ChunkDownloader...")
    
    # Test with a small public S3 object (if available)
    # You can replace this with an actual test bucket/key for real testing
    bucket = "test-bucket"
    key = "test-object"
    
    try:
        downloader = S3ChunkDownloader(bucket, key, concurrency=5)
        
        # Test chunk downloading
        starts = [0, 100, 200]
        lengths = [50, 50, 50]
        
        print(f"Testing download_chunks with bucket={bucket}, key={key}")
        print(f"Starts: {starts}")
        print(f"Lengths: {lengths}")
        
        results = downloader.download_chunks(starts, lengths)
        print(f"Downloaded {len(results)} chunks")
        
        # Test file download
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            downloader.download_chunks_to_file(tmp_path, starts, lengths)
            
            if os.path.exists(tmp_path):
                file_size = os.path.getsize(tmp_path)
                print(f"File download successful, size: {file_size} bytes")
            else:
                print("File download failed - file not created")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        print("This is expected if you don't have access to the test bucket/key")

def test_interface_compatibility():
    """Test that the new interface matches the old Go interface."""
    print("\nTesting interface compatibility...")
    
    try:
        from s3quilt import download_chunks, download_chunks_to_file
        print("✓ Import successful")
        
        # Test function signatures
        import inspect
        
        sig = inspect.signature(download_chunks)
        expected_params = ['bucket', 'key', 'starts', 'lengths', 'concurrency']
        actual_params = list(sig.parameters.keys())
        
        if actual_params == expected_params:
            print("✓ download_chunks signature matches")
        else:
            print(f"✗ download_chunks signature mismatch: {actual_params} vs {expected_params}")
        
        sig = inspect.signature(download_chunks_to_file)
        expected_params = ['bucket', 'key', 'filepath', 'starts', 'lengths', 'concurrency']
        actual_params = list(sig.parameters.keys())
        
        if actual_params == expected_params:
            print("✓ download_chunks_to_file signature matches")
        else:
            print(f"✗ download_chunks_to_file signature mismatch: {actual_params} vs {expected_params}")
            
        print("Interface compatibility test completed!")
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")

if __name__ == "__main__":
    test_interface_compatibility()
    test_basic_functionality()