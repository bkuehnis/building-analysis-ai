#!/usr/bin/env python3
"""
MCP Server for Werk Building Database
Provides access to building data, metadata, and images via MCP endpoints
"""

import json
import base64
from pathlib import Path
from typing import Optional
import fastmcp
from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn
import threading

# Initialize the MCP server
mcp = fastmcp.FastMCP("Werk Buildings", "1.0.0")

# Create separate FastAPI app for serving images
image_app = FastAPI()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data/werk"


# Helper functions
def get_building_ids() -> list:
    """Get all available building IDs"""
    if not DATA_DIR.exists():
        return []
    return sorted([d.name for d in DATA_DIR.iterdir() if d.is_dir()])


def load_json_file(file_path: Path) -> dict:
    """Load and parse a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Failed to load file: {str(e)}"}


def get_building_dir(building_id: str) -> Optional[Path]:
    """Get the directory for a building ID"""
    building_dir = DATA_DIR / building_id
    if building_dir.exists() and building_dir.is_dir():
        return building_dir
    return None


def image_to_base64(image_path: Path) -> Optional[str]:
    """Convert an image file to base64 string"""
    try:
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        return None


# MCP Endpoints

@mcp.tool()
def list_buildings() -> dict:
    """List all available buildings with their IDs"""
    building_ids = get_building_ids()
    return {
        "count": len(building_ids),
        "buildings": building_ids
    }


@mcp.tool()
def get_building_data(building_id: str) -> dict:
    """
    Get all data for a building including datasheet and metadata
    
    Args:
        building_id: The building ID (e.g., "60097")
    
    Returns:
        Dictionary with datasheet, metadata, and image list
    """
    building_dir = get_building_dir(building_id)
    if not building_dir:
        return {"error": f"Building {building_id} not found"}
    
    result = {
        "id": building_id,
        "datasheet": {},
        "metadata": [],
        "images": []
    }
    
    # Load datasheet
    datasheet_file = building_dir / "datasheet.json"
    if datasheet_file.exists():
        result["datasheet"] = load_json_file(datasheet_file)
    else:
        result["datasheet"] = {"note": "datasheet.json not found"}
    
    # Load metadata and build image list
    metadata_file = building_dir / "metadata.json"
    if metadata_file.exists():
        metadata = load_json_file(metadata_file)
        result["metadata"] = metadata if isinstance(metadata, list) else []
        
        # Build image list with info
        if isinstance(metadata, list):
            for img in metadata:
                if isinstance(img, dict) and "id" in img:
                    result["images"].append({
                        "id": img.get("id"),
                        "name": img.get("name", ""),
                        "order": img.get("order", 0),
                        "mimeType": img.get("mimeType", "image/jpeg"),
                        "width": img.get("width"),
                        "height": img.get("height")
                    })
    
    return result


@mcp.tool()
def get_datasheet(building_id: str) -> dict:
    """
    Get the parsed datasheet (HTML converted to JSON) for a building
    
    Args:
        building_id: The building ID (e.g., "60097")
    
    Returns:
        Dictionary with building information
    """
    building_dir = get_building_dir(building_id)
    if not building_dir:
        return {"error": f"Building {building_id} not found"}
    
    datasheet_file = building_dir / "datasheet.json"
    if not datasheet_file.exists():
        return {"error": f"Datasheet not found for building {building_id}"}
    
    return load_json_file(datasheet_file)


@mcp.tool()
def get_metadata(building_id: str) -> dict:
    """
    Get metadata (image list) for a building
    
    Args:
        building_id: The building ID (e.g., "60097")
    
    Returns:
        List of image metadata
    """
    building_dir = get_building_dir(building_id)
    if not building_dir:
        return {"error": f"Building {building_id} not found"}
    
    metadata_file = building_dir / "metadata.json"
    if not metadata_file.exists():
        return {"error": f"Metadata not found for building {building_id}"}
    
    metadata = load_json_file(metadata_file)
    return {
        "id": building_id,
        "image_count": len(metadata) if isinstance(metadata, list) else 0,
        "images": metadata
    }


@mcp.tool()
def list_images(building_id: str, include_data: bool = False) -> dict:
    """
    List all images available for a building
    
    Args:
        building_id: The building ID (e.g., "60097")
        include_data: If True, includes base64-encoded image data (default: False)
    
    Returns:
        List of images with metadata and optionally base64 data
    """
    building_dir = get_building_dir(building_id)
    if not building_dir:
        return {"error": f"Building {building_id} not found"}
    
    # Check which image files exist
    images = []
    
    # Get metadata to know which images should exist
    metadata_file = building_dir / "metadata.json"
    if metadata_file.exists():
        metadata = load_json_file(metadata_file)
        if isinstance(metadata, list):
            for img_info in metadata:
                if isinstance(img_info, dict):
                    img_id = img_info.get("id")
                    img_name = img_info.get("name", "")
                    img_order = img_info.get("order", 0)
                    mime_type = img_info.get("mimeType", "image/jpeg")
                    
                    # Find the actual image file
                    for img_file in building_dir.glob(f"{img_order:02d}_*"):
                        if img_file.is_file():
                            image_entry = {
                                "id": img_id,
                                "order": img_order,
                                "name": img_name,
                                "filename": img_file.name,
                                "size": img_file.stat().st_size,
                                "mimeType": mime_type,
                                "width": img_info.get("width"),
                                "height": img_info.get("height"),
                                "retrieve_with": f"get_image(building_id='{building_id}', image_id={img_id})"
                            }
                            
                            # Optionally include base64 data
                            if include_data:
                                base64_data = image_to_base64(img_file)
                                if base64_data:
                                    image_entry["data"] = base64_data
                                    image_entry["data_url"] = f"data:{mime_type};base64,{base64_data}"
                            
                            images.append(image_entry)
                            break
    
    return {
        "building_id": building_id,
        "image_count": len(images),
        "images": images,
        "note": "Use get_image(building_id, image_id) to retrieve individual images with base64 data"
    }


@mcp.tool()
def get_image(building_id: str, image_id: int) -> dict:
    """
    Get a specific image as a markdown link
    
    Args:
        building_id: The building ID (e.g., "60097")
        image_id: The image ID (e.g., 68602)
    
    Returns:
        Markdown formatted image link
    """
    building_dir = get_building_dir(building_id)
    if not building_dir:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Building {building_id} not found"
                }
            ]
        }
    
    # Get image metadata from metadata.json to find the order number
    image_metadata = {}
    image_order = None
    metadata_file = building_dir / "metadata.json"
    
    if metadata_file.exists():
        metadata = load_json_file(metadata_file)
        if isinstance(metadata, list):
            for img_info in metadata:
                if isinstance(img_info, dict) and img_info.get("id") == image_id:
                    image_metadata = img_info
                    image_order = img_info.get("order")
                    break
    
    if image_order is None:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Image {image_id} not found in metadata for building {building_id}"
                }
            ]
        }
    
    # Find the image file using the order number
    image_file = None
    for img in building_dir.glob(f"{image_order:02d}_*"):
        if img.is_file() and img.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
            image_file = img
            break
    
    if not image_file:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Image file for image_id {image_id} (order {image_order}) not found for building {building_id}"
                }
            ]
        }
    
    # Generate image URL (using port 8001 for image server)
    image_url = f"http://localhost:8001/images/{building_id}/{image_id}"
    image_name = image_metadata.get("name", f"Image {image_id}")
    
    # Return markdown formatted image link
    return {
        "content": [
            {
                "type": "text",
                "text": f"![{image_name}]({image_url})"
            }
        ]
    }


@mcp.tool()
def search_buildings(query: str) -> dict:
    """
    Search buildings by name, architect, location, or other fields
    
    Args:
        query: Search term (e.g., "Zürich", "Architekt", "2011")
    
    Returns:
        List of matching buildings
    """
    building_ids = get_building_ids()
    results = []
    query_lower = query.lower()
    
    for building_id in building_ids:
        building_dir = get_building_dir(building_id)
        if not building_dir:
            continue
        
        # Load datasheet
        datasheet_file = building_dir / "datasheet.json"
        if datasheet_file.exists():
            datasheet = load_json_file(datasheet_file)
            
            # Search in datasheet fields
            match_fields = []
            for key, value in datasheet.items():
                if isinstance(value, str) and query_lower in value.lower():
                    match_fields.append(key)
            
            if match_fields:
                results.append({
                    "building_id": building_id,
                    "name": datasheet.get("Name", ""),
                    "location": datasheet.get("Ort", ""),
                    "year": datasheet.get("Fertigstellung", ""),
                    "matched_fields": match_fields
                })
    
    return {
        "query": query,
        "count": len(results),
        "results": results
    }


# FastAPI endpoint for serving images on separate port
@image_app.get("/images/{building_id}/{image_id}")
async def serve_image(building_id: str, image_id: int):
    """
    Serve a specific image file
    
    Args:
        building_id: The building ID
        image_id: The image ID
    
    Returns:
        The image file
    """
    building_dir = get_building_dir(building_id)
    if not building_dir:
        return {"error": f"Building {building_id} not found"}
    
    # Get image metadata to find the order number
    image_order = None
    image_metadata = {}
    metadata_file = building_dir / "metadata.json"
    
    if metadata_file.exists():
        metadata = load_json_file(metadata_file)
        if isinstance(metadata, list):
            for img_info in metadata:
                if isinstance(img_info, dict) and img_info.get("id") == image_id:
                    image_metadata = img_info
                    image_order = img_info.get("order")
                    break
    
    if image_order is None:
        return {"error": f"Image {image_id} not found in metadata"}
    
    # Find the image file
    image_file = None
    for img in building_dir.glob(f"{image_order:02d}_*"):
        if img.is_file() and img.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
            image_file = img
            break
    
    if not image_file or not image_file.exists():
        return {"error": f"Image file not found for order {image_order}"}
    
    return FileResponse(image_file)


def run_server(host: str = "localhost", mcp_port: int = 8000, image_port: int = 8001):
    """Run the MCP server and image server on separate ports"""
    print("Starting Werk Buildings Server...")
    print(f"Data directory: {DATA_DIR}")
    
    # Check if data directory exists
    if not DATA_DIR.exists():
        print(f"Warning: Data directory not found at {DATA_DIR}")
    else:
        building_count = len(get_building_ids())
        print(f"Available buildings: {building_count}")
    
    print(f"\nMCP Server: http://{host}:{mcp_port}/mcp")
    print(f"Image Server: http://{host}:{image_port}/images/{{building_id}}/{{image_id}}")
    print(f"\nExample image URL: http://{host}:{image_port}/images/60097/66276\n")
    
    # Start image server in a separate thread
    def run_image_server():
        uvicorn.run(image_app, host=host, port=image_port, log_level="info")
    
    image_thread = threading.Thread(target=run_image_server, daemon=True)
    image_thread.start()
    
    # Run the MCP server on main thread
    mcp.run(transport="http", port=mcp_port)


if __name__ == "__main__":
    import sys
    
    mcp_port = 8000
    image_port = 8001
    
    if len(sys.argv) > 1:
        mcp_port = int(sys.argv[1])
    if len(sys.argv) > 2:
        image_port = int(sys.argv[2])
    
    run_server(mcp_port=mcp_port, image_port=image_port)
