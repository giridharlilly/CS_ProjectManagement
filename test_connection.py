"""
test_connection.py
==================
Test OneLake Lakehouse connection.
"""

from db_connection import test_connection, WORKSPACE_NAME, LAKEHOUSE_NAME, _list_files


def main():
    print("=" * 60)
    print("  Lakehouse Connection Test (OneLake HTTPS)")
    print("=" * 60)
    print(f"  Workspace: {WORKSPACE_NAME}")
    print(f"  Lakehouse: {LAKEHOUSE_NAME}")
    print("-" * 60)

    if not test_connection():
        print("\nFAILED - Cannot connect.")
        return

    print("\nSUCCESS - Connected!\n")

    # List contents
    print("Lakehouse contents:")
    try:
        files = _list_files("Files")
        if files:
            for f in files:
                print(f"  {'[DIR]' if f.get('isDirectory') == 'true' else '     '} {f['name']}")
        else:
            print("  (empty — ready for data)")
    except Exception as e:
        print(f"  Could not list: {e}")

    print("\nTables folder:")
    try:
        tables = _list_files("Tables")
        if tables:
            for t in tables:
                print(f"  {'[DIR]' if t.get('isDirectory') == 'true' else '     '} {t['name']}")
        else:
            print("  (empty)")
    except Exception as e:
        print(f"  Could not list: {e}")


if __name__ == "__main__":
    main()
