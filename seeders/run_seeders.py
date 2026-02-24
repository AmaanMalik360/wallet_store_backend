#!/usr/bin/env python
"""
Database Seeder Runner - Run by filename
Usage:
    python seeders/run_seeders.py category_seeder.py              # Run specific seeder
    python seeders/run_seeders.py seeders/category_seeder.py     # Run with path
    python seeders/run_seeders.py --all                          # Run all seeders
    python seeders/run_seeders.py category_seeder.py --clear     # Clear and run
"""

import sys
from pathlib import Path
import importlib.util
import argparse

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.models.db import get_db

def run_seeder_file(seeder_path: str, db_session, clear_first: bool = False):
    """Run a seeder by filename"""
    seeder_file = Path(seeder_path)
    
    # If just filename is provided, look in seeders directory
    if not seeder_file.exists() and not seeder_file.parent.name:
        seeder_file = Path(__file__).parent / seeder_file
    
    if not seeder_file.exists():
        print(f"❌ Seeder file not found: {seeder_file}")
        return False
    
    print(f"\n📦 Running seeder: {seeder_file.name}")
    
    # Import the module
    module_name = seeder_file.stem
    spec = importlib.util.spec_from_file_location(module_name, seeder_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Find the seeder class (look for class that inherits from BaseSeeder but is not BaseSeeder)
    seeder_class = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        # Check if it's a class, has seed method, and is not BaseSeeder
        if (isinstance(attr, type) and 
            hasattr(attr, 'seed') and 
            attr.__name__ != 'BaseSeeder'):
            seeder_class = attr
            break
    
    if not seeder_class:
        print(f"❌ No seeder class found in {seeder_file.name}")
        print("   Make sure your seeder class has a 'seed()' method")
        return False
    
    # Run the seeder
    try:
        seeder = seeder_class(db_session)
        
        if clear_first and hasattr(seeder, 'clear'):
            print(f"🗑️  Clearing data...")
            seeder.clear()
            db_session.commit()
        
        print(f"🌱 Seeding...")
        seeder.seed()
        db_session.commit()
        print(f"✅ {seeder_file.name} completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error running seeder: {str(e)}")
        db_session.rollback()
        return False

def run_all_seeders(db_session, clear_first: bool = False):
    """Run all seeder files in the seeders directory"""
    seeders_dir = Path(__file__).parent
    
    # Get all Python files that end with '_seeder.py' but not this runner
    seeder_files = sorted([
        f for f in seeders_dir.glob("*_seeder.py") 
        if f.name != "run_seeders.py"  # Exclude this runner
    ])
    
    if not seeder_files:
        print("❌ No seeder files found!")
        return
    
    print(f"🌱 Found {len(seeder_files)} seeder(s) to run...")
    
    success_count = 0
    for seeder_file in seeder_files:
        if run_seeder_file(str(seeder_file), db_session, clear_first):
            success_count += 1
    
    print(f"\n✅ {success_count}/{len(seeder_files)} seeders completed successfully")

def list_seeders():
    """List all available seeder files"""
    seeders_dir = Path(__file__).parent
    seeder_files = sorted([
        f for f in seeders_dir.glob("*_seeder.py")
        if f.name != "run_seeders.py"
    ])
    
    print("\n📋 Available seeders:")
    for seeder_file in seeder_files:
        print(f"  - {seeder_file.name}")

def main():
    parser = argparse.ArgumentParser(description="Run database seeders by filename")
    parser.add_argument(
        "seeder",
        nargs="?",
        help="Seeder filename to run (e.g., category_seeder.py)"
    )
    parser.add_argument(
        "--clear", "-c",
        action="store_true",
        help="Clear existing data before seeding"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all seeders"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available seeders"
    )
    
    args = parser.parse_args()
    
    # Handle list command
    if args.list:
        list_seeders()
        return
    
    # Get database session
    db_session = next(get_db())
    
    try:
        if args.all:
            # Run all seeders
            run_all_seeders(db_session, args.clear)
        elif args.seeder:
            # Run specific seeder by filename
            run_seeder_file(args.seeder, db_session, args.clear)
        else:
            # No arguments provided
            print("❌ Please specify a seeder or use --all")
            print("\nUsage:")
            print("  python seeders/run_seeders.py category_seeder.py")
            print("  python seeders/run_seeders.py --all")
            print("  python seeders/run_seeders.py --list")
            
    finally:
        db_session.close()

if __name__ == "__main__":
    main()