"""
Migration script to add created_by column to todos table.

This script:
1. Adds a new 'created_by' column to the todos table
2. Populates existing rows with 'task created by <username>' from the users table
3. Can be run safely multiple times (idempotent)

Usage:
    python backend/migrations/add_created_by_column.py
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


async def run_migration():
    """Run the migration to add created_by column."""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Create async engine
    engine = create_async_engine(database_url, echo=True)
    
    async with engine.begin() as conn:
        # Check if column already exists
        check_column = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='todos' AND column_name='created_by';
        """
        result = await conn.execute(text(check_column))
        column_exists = result.fetchone() is not None
        
        if column_exists:
            print("✓ Column 'created_by' already exists in todos table")
        else:
            print("Adding 'created_by' column to todos table...")
            
            # Add the column
            add_column_sql = """
            ALTER TABLE todos 
            ADD COLUMN created_by VARCHAR(100);
            """
            await conn.execute(text(add_column_sql))
            print("✓ Column 'created_by' added successfully")
        
        # Update existing rows with username from users table
        print("Populating created_by for existing tasks...")
        
        update_sql = """
        UPDATE todos 
        SET created_by = CONCAT('task created by ''', users.username, '''')
        FROM users 
        WHERE todos.user_id = users.id 
        AND todos.created_by IS NULL;
        """
        result = await conn.execute(text(update_sql))
        rows_updated = result.rowcount
        
        print(f"✓ Updated {rows_updated} existing task(s) with created_by information")
        
        # Show sample of updated data
        print("\nSample of updated tasks:")
        sample_sql = """
        SELECT id, title, created_by 
        FROM todos 
        WHERE created_by IS NOT NULL 
        LIMIT 5;
        """
        result = await conn.execute(text(sample_sql))
        rows = result.fetchall()
        
        if rows:
            for row in rows:
                print(f"  Task #{row[0]}: {row[1][:40]}... - {row[2]}")
        else:
            print("  No tasks found in database")
    
    await engine.dispose()
    print("\n✅ Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())
