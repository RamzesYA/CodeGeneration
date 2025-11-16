import re
import json
import sys
from typing import List, Dict, Any, Optional


# ============================================================
#   ПАРСЕР ДИАГРАММИ КЛАССОВ (старый функционал)
# ============================================================
class PlantUMLParser:
    def __init__(self):
        self.classes = []
        self.relationships = []
        self.current_class = None

    def parse_file(self, filename: str) -> Dict[str, Any]:
        """Чтение и парсинг файла"""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()
            return self.parse_content(content)
        except FileNotFoundError:
            print(f"Ошибка: Файл '{filename}' не найден.")
            sys.exit(1)
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            sys.exit(1)

    def parse_content(self, content: str) -> Dict[str, Any]:
        """Парсинг классовой диаграммы PlantUML"""
        lines = content.split('\n')

        for line in lines:
            line = line.strip()

            if not line or line.startswith("'") or line.startswith('@startuml') or line.startswith('@enduml'):
                continue

            if line.startswith('class '):
                self.parse_class(line)
            elif any(symbol in line for symbol in ['<|--', '--', 'o--', '*--', '..>']):
                self.parse_relationship(line)
            elif line.startswith('{') or (self.current_class and ('}' not in line)):
                self.parse_class_content(line)

        return self.to_json()

    # --- Остальной код твоего классового парсера (без изменений) ---
    def parse_class(self, line: str):
        class_match = re.match(r'class\s+(\w+)\s*\{?', line)
        if class_match:
            class_name = class_match.group(1)
            self.current_class = {
                "name": class_name,
                "attributes": [],
                "methods": [],
                "inherits": None
            }
            self.classes.append(self.current_class)

    def parse_class_content(self, line: str):
        if not self.current_class:
            return

        clean_line = re.sub(r'^\s*\{[^}]*\}\s*', '', line.strip())
        clean_line = clean_line.rstrip('}')

        if not clean_line or clean_line == '}':
            return

        attribute_match = re.match(r'^(-|\+)\s*(\w+)\s*:\s*([^()]+)$', clean_line)
        if attribute_match:
            visibility, name, data_type = attribute_match.groups()
            if visibility == '-':
                self.current_class["attributes"].append({
                    "name": name.strip(),
                    "type": data_type.strip()
                })
            return

        method_match = re.match(r'^(\+|\-)\s*(\w+)\s*\((.*)\)\s*:\s*([^()]+)$', clean_line)
        if method_match:
            visibility, name, params_str, return_type = method_match.groups()
            if visibility == '+':
                params = self.parse_method_params(params_str)
                self.current_class["methods"].append({
                    "name": name.strip(),
                    "return_type": return_type.strip(),
                    "params": params
                })

    def parse_method_params(self, params_str: str) -> List[Dict[str, str]]:
        params = []
        if not params_str.strip():
            return params

        for param in params_str.split(','):
            param = param.strip()
            if ':' in param:
                name, param_type = param.split(':', 1)
                params.append({"name": name.strip(), "type": param_type.strip()})
        return params

    def parse_relationship(self, line: str):
        relationship_type = None
        multiplicity = "one-to-one"

        if '<|--' in line:
            relationship_type = "inheritance"
            parts = line.split('<|--')
            if len(parts) == 2:
                parent = self.clean_class_name(parts[0].strip())
                child = self.clean_class_name(parts[1].strip())
                for cls in self.classes:
                    if cls["name"] == child:
                        cls["inherits"] = parent
                self.relationships.append({
                    "type": relationship_type,
                    "from": child,
                    "to": parent,
                    "multiplicity": multiplicity
                })
            return

        if '..>' in line:
            relationship_type = "dependency"
            line = line.replace('..>', '--')
        elif 'o--' in line:
            relationship_type = "aggregation"
            line = line.replace('o--', '--')
        elif '*--' in line:
            relationship_type = "composition"
            line = line.replace('*--', '--')
        else:
            relationship_type = "association"

        pattern = r'\"([^\"]*)\"?\s*--\s*\"([^\"]*)\"?'
        match = re.search(pattern, line)

        if match:
            left_part, right_part = match.groups()
            left_class = self.extract_class_name(left_part)
            right_class = self.extract_class_name(right_part)
            multiplicity = self.determine_multiplicity(left_part, right_part)
            self.relationships.append({
                "type": relationship_type,
                "from": left_class,
                "to": right_class,
                "multiplicity": multiplicity
            })

    def clean_class_name(self, class_name: str) -> str:
        return re.sub(r'[\"0-9.*]', '', class_name).strip()

    def extract_class_name(self, part: str) -> str:
        return re.sub(r'[\"0-9.*]', '', part).strip()

    def determine_multiplicity(self, left: str, right: str) -> str:
        left_mult = self.parse_multiplicity(left)
        right_mult = self.parse_multiplicity(right)

        if left_mult == "one" and right_mult == "one":
            return "one-to-one"
        elif left_mult == "one" and right_mult == "many":
            return "one-to-many"
        elif left_mult == "many" and right_mult == "one":
            return "many-to-one"
        else:
            return "many-to-many"

    def parse_multiplicity(self, part: str) -> str:
        if '0..*' in part or '1..*' in part or '*' in part:
            return "many"
        else:
            return "one"

    def to_json(self) -> Dict[str, Any]:
        return {
            "classes": self.classes,
            "relationships": self.relationships
        }


# ============================================================
#   НОВЫЙ ФУНКЦИОНАЛ: ПАРСЕР DEPLOYMENT DIAGRAM
# ============================================================
class DeploymentDiagramParser:
    """Парсер диаграммы развертывания."""

    NODE_PATTERN = r'node\s+"([^"]+)"'
    CONNECTION_PATTERN = r'"([^"]+)"\s*-->\s*"([^"]+)"\s*:\s*(.+)'

    def parse(self, content: str) -> Dict[str, Any]:
        nodes = []
        node_set = set()
        connections = []

        for match in re.finditer(self.NODE_PATTERN, content):
            name = match.group(1).strip()
            if name not in node_set:
                node_set.add(name)
                nodes.append({"name": name})

        for match in re.finditer(self.CONNECTION_PATTERN, content):
            src = match.group(1).strip()
            dst = match.group(2).strip()
            label = match.group(3).strip()

            connections.append({
                "from": src,
                "to": dst,
                "label": label
            })

        return {
            "nodes": nodes,
            "connections": connections
        }


# ============================================================
#   ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def save_to_json(data: Dict[str, Any], filename: str):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Сохранено в {filename}")
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")


def detect_diagram_type(text: str) -> str:
    """Определяет тип диаграммы."""
    if "node " in text or "-->" in text:
        return "deployment"
    if "class " in text:
        return "class"
    return "unknown"


# ============================================================
#   MAIN
# ============================================================
def main():
    print("=== PlantUML → JSON Parser ===")

    filename = input("Введите путь к файлу PlantUML: ").strip()
    if not filename:
        print("Ошибка: не указан файл.")
        return

    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Ошибка чтения: {e}")
        return

    diagram_type = detect_diagram_type(content)
    print(f"\nОбнаружен тип диаграммы: {diagram_type}")

    if diagram_type == "class":
        parser = PlantUMLParser()
        result = parser.parse_content(content)
        save_to_json(result, "classes.json")

    elif diagram_type == "deployment":
        parser = DeploymentDiagramParser()
        result = parser.parse(content)
        save_to_json(result, "deployment.json")

    else:
        print("❌ Не удалось определить тип диаграммы.")
        return

    print("\nГотово!")


if __name__ == "__main__":
    main()
