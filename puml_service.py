"""Service wrapper to parse PlantUML text and return JSON-serializable dict.

This module re-uses parsers defined in `puml2json.py` and exposes a simple
function `parse_puml_to_json(puml: str) -> dict` suitable for server integration.
"""
from typing import Dict, Any

try:
    from puml2json import (
        detect_diagram_type,
        PlantUMLParser,
        DeploymentDiagramParser,
        DatabaseDiagramParser,
    )
except Exception as e:
    # If import fails, raise on usage time
    detect_diagram_type = None
    PlantUMLParser = None
    DeploymentDiagramParser = None
    DatabaseDiagramParser = None


def parse_puml_to_json(puml: str) -> Dict[str, Any]:
    """Parse PlantUML string and return JSON-like dict.

    Returns a dict. On error returns {"error": "message"}.
    """
    if not isinstance(puml, str):
        return {"error": "puml must be a string"}

    if detect_diagram_type is None:
        return {"error": "puml2json module not importable"}

    try:
        diagram_type = detect_diagram_type(puml)
        if diagram_type == "class":
            parser = PlantUMLParser()
            result = parser.parse_content(puml)
        elif diagram_type == "deployment":
            parser = DeploymentDiagramParser()
            result = parser.parse(puml)
        elif diagram_type == "database":
            parser = DatabaseDiagramParser()
            result = parser.parse(puml)
        else:
            result = {"error": "unknown diagram type"}
        return result
    except Exception as e:
        return {"error": f"parsing failed: {e}"}
