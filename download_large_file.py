import os
import urllib.request

LARGE_DOCS_DIR = os.path.join("tests", "test_docs_large")

# Ensure the large document directory exists
if not os.path.exists(LARGE_DOCS_DIR):
    os.makedirs(LARGE_DOCS_DIR)

TARGET_FILE = os.path.join(LARGE_DOCS_DIR, "shakespeare_complete_works.txt")

# URL for Project Gutenberg's Complete Works of William Shakespeare (~5.5 MB)
URL = "https://www.gutenberg.org/cache/epub/100/pg100.txt"


def download_file():
    if os.path.exists(TARGET_FILE):
        print(f"File already exists: {TARGET_FILE}")
        return

    print(f"Downloading 5.5MB text file from {URL}...")
    try:
        urllib.request.urlretrieve(URL, TARGET_FILE)
        size_mb = os.path.getsize(TARGET_FILE) / (1024 * 1024)
        print(f"Download complete! Saved to {TARGET_FILE} ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"Failed to download file: {e}")


if __name__ == "__main__":
    download_file()
