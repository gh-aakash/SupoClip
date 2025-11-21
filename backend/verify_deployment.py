#!/usr/bin/env python3
"""
Deployment verification script - Run this in Docker to verify all integrations.
"""
import sys
import traceback

def test_imports():
    """Test all critical imports."""
    print("=" * 60)
    print("TESTING IMPORTS")
    print("=" * 60)
    
    try:
        # Core dependencies
        import fastapi
        print("✓ fastapi")
        
        import uvicorn
        print("✓ uvicorn")
        
        import sqlalchemy
        print("✓ sqlalchemy")
        
        import asyncpg
        print("✓ asyncpg")
        
        # Application modules
        from src.models import User, Task, Source, GeneratedClip
        print("✓ models (User, Task, Source, GeneratedClip)")
        
        from src.database import engine, get_db, init_db
        print("✓ database (engine, get_db, init_db)")
        
        from src.utils.validators import validate_youtube_url, validate_task_input
        print("✓ validators (validate_youtube_url, validate_task_input)")
        
        from src.api.routes.tasks import router
        print("✓ task routes")
        
        from src.workers.job_queue import JobQueue
        print("✓ job queue")
        
        from src.config import Config
        print("✓ config")
        
        print("\n✅ All imports successful!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        traceback.print_exc()
        return False


def test_validators():
    """Test URL validation logic."""
    print("=" * 60)
    print("TESTING VALIDATORS")
    print("=" * 60)
    
    try:
        from src.utils.validators import validate_youtube_url, validate_task_input
        from fastapi import HTTPException
        
        # Test valid YouTube URLs
        valid_urls = [
            'https://www.youtube.com/watch?v=test',
            'https://youtube.com/watch?v=test',
            'https://youtu.be/test',
            'https://m.youtube.com/watch?v=test'
        ]
        
        for url in valid_urls:
            try:
                validate_youtube_url(url)
                print(f"✓ Valid URL accepted: {url}")
            except HTTPException as e:
                print(f"✗ Valid URL rejected: {url} - {e.detail}")
                return False
        
        # Test invalid URLs
        invalid_urls = [
            'https://evil.com/video',
            'https://vimeo.com/video',
            'http://localhost/video'
        ]
        
        for url in invalid_urls:
            try:
                validate_youtube_url(url)
                print(f"✗ Invalid URL accepted: {url}")
                return False
            except HTTPException:
                print(f"✓ Invalid URL rejected: {url}")
        
        # Test task input validation
        valid_data = {
            'source': {'url': 'https://youtube.com/watch?v=test'},
            'font_options': {'font_size': 24}
        }
        result = validate_task_input(valid_data)
        print("✓ Valid task input accepted")
        
        # Test invalid font size
        invalid_data = {
            'source': {'url': 'https://youtube.com/watch?v=test'},
            'font_options': {'font_size': 200}
        }
        try:
            validate_task_input(invalid_data)
            print("✗ Invalid font size accepted")
            return False
        except HTTPException:
            print("✓ Invalid font size rejected")
        
        print("\n✅ All validator tests passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Validator test failed: {e}")
        traceback.print_exc()
        return False


def test_models():
    """Test model definitions."""
    print("=" * 60)
    print("TESTING MODELS")
    print("=" * 60)
    
    try:
        from src.models import User, Task, Source, GeneratedClip
        from sqlalchemy import Index
        
        # Check Task indexes
        task_indexes = [arg for arg in Task.__table_args__ if isinstance(arg, Index)]
        print(f"✓ Task model has {len(task_indexes)} indexes")
        
        index_names = [idx.name for idx in task_indexes]
        expected_indexes = ['idx_task_user_id', 'idx_task_status', 'idx_task_created_at']
        for expected in expected_indexes:
            if expected in index_names:
                print(f"  ✓ {expected}")
            else:
                print(f"  ✗ Missing index: {expected}")
                return False
        
        # Check GeneratedClip indexes
        clip_indexes = [arg for arg in GeneratedClip.__table_args__ if isinstance(arg, Index)]
        print(f"✓ GeneratedClip model has {len(clip_indexes)} indexes")
        
        if 'idx_clip_task_id' in [idx.name for idx in clip_indexes]:
            print("  ✓ idx_clip_task_id")
        else:
            print("  ✗ Missing index: idx_clip_task_id")
            return False
        
        print("\n✅ All model tests passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Model test failed: {e}")
        traceback.print_exc()
        return False


def test_database_config():
    """Test database configuration."""
    print("=" * 60)
    print("TESTING DATABASE CONFIG")
    print("=" * 60)
    
    try:
        from src.database import engine
        
        # Check connect_args
        connect_args = engine.pool._creator.keywords.get('connect_args', {})
        
        if connect_args.get('ssl') == 'require':
            print("✓ SSL configured correctly")
        else:
            print("✗ SSL not configured")
            return False
        
        if connect_args.get('statement_cache_size') == 0:
            print("✓ Prepared statements disabled (pgbouncer compatible)")
        else:
            print("✗ statement_cache_size not set to 0")
            return False
        
        print("\n✅ Database config tests passed!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Database config test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("SUPOCLIP DEPLOYMENT VERIFICATION")
    print("=" * 60 + "\n")
    
    results = {
        'imports': test_imports(),
        'validators': test_validators(),
        'models': test_models(),
        'database': test_database_config()
    }
    
    print("=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.upper()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED - READY FOR DEPLOYMENT! 🎉\n")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - FIX BEFORE DEPLOYING ❌\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
