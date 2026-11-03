import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect(
            user="postgres",
            password="atdesk_staging",
            host="127.0.0.1",
            port=5433,
            database="postgres"
        )
        row = await conn.fetchrow("SELECT 1 FROM pg_database WHERE datname='atdesk_staging'")
        if not row:
            await conn.execute("CREATE DATABASE atdesk_staging;")
            print("PostgreSQL Database 'atdesk_staging' created successfully on port 5433.")
        else:
            print("PostgreSQL Database 'atdesk_staging' already exists on port 5433.")
        await conn.close()
    except Exception as e:
        print(f"Error creating PostgreSQL database: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(main())

