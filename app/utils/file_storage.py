from pathlib import Path


def save_file(content: bytes, filename: str, folder: str = "uploads") -> str:
    path = Path(folder)
    path.mkdir(parents=True, exist_ok=True)

    file_path = path / filename
    file_path.write_bytes(content)
    
    return str(file_path)
