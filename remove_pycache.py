import os
import shutil

def delete_pycache_folders(base_path):
    """
    Recursively delete all __pycache__ folders in the given base path.
    
    Args:
        base_path (str): The root directory to start the search.
    """
    for root, dirs, files in os.walk(base_path):
        for dir_name in dirs:
            if dir_name == "__pycache__":
                folder_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(folder_path)
                    print(f"Deleted: {folder_path}")
                except Exception as e:
                    print(f"Failed to delete {folder_path}: {e}")

if __name__ == "__main__":
    cwd = os.getcwd()
    print(f"Current Working Directory: {cwd}")

    if os.path.exists(cwd):
        delete_pycache_folders(cwd)
    else:
        print(f"The path '{cwd}' does not exist.")
