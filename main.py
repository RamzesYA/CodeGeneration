import json
import re
from pathlib import Path
from typing import Dict, Any
from jinja2 import Template


class Generator:
    """ Базовый класс генератора """

    def __init__(self, file_path: str, template_file: str, output_file: str):
        self.file_path = Path(file_path)
        self.template_file = Path(template_file)
        self.output_file = Path(output_file)

    def load_json(self) -> Dict[str, Any]:
        """ Загружает JSON-файл """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Файл {self.file_path} не найден.")

        with self.file_path.open(encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                raise ValueError(f"Ошибка при разборе JSON: {e}")

    def parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """ Должен быть реализован в подклассах """
        raise NotImplementedError

    def generate(self) -> None:
        """ Генерирует код на основе данных и шаблона """
        data = self.load_json()
        parsed_data = self.parse_data(data)

        if not self.template_file.exists():
            raise FileNotFoundError(f"Шаблон не найден: {self.template_file}")

        with self.template_file.open(encoding="utf-8") as file:
            template_str = file.read()

        template = Template(template_str)
        output_content = template.render(parsed_data)

        with self.output_file.open("w", encoding="utf-8") as file:
            file.write(output_content)

        print(f"Сгенерированный файл записан: {self.output_file}")


class SQLGenerator(Generator):
    """ Генератор SQL-кода """

    def parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """ Разбирает JSON-схему базы данных """
        tables = data.get("tables", [])
        parsed_data = {"tables": []}

        for table in tables:
            parsed_table = {
                "name": table["name"],
                "columns": []
            }

            for column in table.get("columns", []):
                parsed_column = {
                    "name": column["name"],
                    "type": column["type"],
                    "primary_key": column.get("primary_key", False),
                    "auto_increment": column.get("auto_increment", False),
                    "not_null": column.get("not_null", False),
                    "foreign_key": column.get("foreign_key")
                }
                parsed_table["columns"].append(parsed_column)

            parsed_data["tables"].append(parsed_table)

        return parsed_data


class ClassGenerator(Generator):
    """ Генератор Python-классов """

    def parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """ Разбирает JSON-схему UML-диаграммы классов """
        classes = data.get("classes", [])
        parsed_data = {"classes": []}

        for cls in classes:
            methods = []
            for method in cls.get("methods", []):
                params = [(param["name"], param["type"]) for param in method.get("params", [])]
                methods.append({
                    "name": method["name"],
                    "params": params,
                    "return_type": method.get("return_type", "None")
                })

            parsed_data["classes"].append({
                "name": cls.get("name"),
                "attributes": [(attr["name"], attr.get("type", "Any")) for attr in cls.get("attributes", [])],
                "methods": methods,
                "inherits": cls.get("inherits", None)
            })

        return parsed_data


class DockerComposeGenerator(Generator):
    """ Генератор docker-compose.yaml """

    def sanitize_name(self, name: str) -> str:
        name = name.lower().replace(" ", "-")
        name = re.sub(r'[^a-z0-9\-]', '', name)
        name = re.sub(r'-+', '-', name)
        return name.strip("-")

    def parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        nodes = data.get("nodes", [])
        connections = data.get("connections", [])

        service_map = {node["name"]: {
            "name": node["name"],
            "depends_on": []
        } for node in nodes}

        for conn in connections:
            src = conn["from"]
            dest = conn["to"]
            service_map[dest]["depends_on"].append(src)

        parsed_services = []
        for svc in service_map.values():
            sanitized_name = self.sanitize_name(svc["name"])
            depends = [self.sanitize_name(dep) for dep in svc["depends_on"]]
            parsed_services.append({
                "container_name": sanitized_name,
                "depends_on": depends if depends else []
            })

        return {"services": parsed_services}


def detect_generator(file_path: str) -> Generator:
    """ Определяет, что генерировать: SQL, классы или docker-compose """
    with open(file_path, encoding="utf-8") as file:
        data = json.load(file)

    if "tables" in data:
        return SQLGenerator(file_path, "jinja_templates/sql_template.jinja2", "generated_sql/db.sql")
    elif "classes" in data:
        return ClassGenerator(file_path, "jinja_templates/classes.jinja2", "generated_code/classes.py")
    elif "nodes" in data and "connections" in data:
        return DockerComposeGenerator(file_path, "jinja_templates/docker_compose.jinja2", "generated_code/docker-compose.yaml")
    else:
        raise ValueError("Неизвестный формат JSON. Ожидаются ключи 'tables', 'classes' или 'nodes'.")


if __name__ == "__main__":
    file_path = "json_templates/db.json"  # Укажите путь к JSON-файлу
    try:
        generator = detect_generator(file_path)
        generator.generate()
    except Exception as e:
        print("Ошибка:", e)
