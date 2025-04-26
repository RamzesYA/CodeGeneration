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


class MySQLGenerator(SQLGenerator):
    """ Генератор SQL-кода для MySQL """

    def __init__(self, file_path: str):
        super().__init__(file_path, "jinja_templates/mysql_template.jinja2", "generated_sql/mysql_db.sql")


class OracleSQLGenerator(SQLGenerator):
    """ Генератор SQL-кода для Oracle """

    def __init__(self, file_path: str):
        super().__init__(file_path, "jinja_templates/oracle_template.jinja2", "generated_sql/oracle_db.sql")


class PythonClassGenerator(Generator):
    """ Генератор Python-классов с типами """

    def map_type(self, type_name: str) -> str:
        """ Сопоставление типов для Python """
        type_mappings = {
            "int": "int",
            "str": "str",
            "float": "float",
            "bool": "bool",
            "Any": "Any"
        }
        if type_name.startswith("List["):
            inner_type = type_name[5:-1]
            return f"List[{self.map_type(inner_type)}]"
        return type_mappings.get(type_name, type_name)

    def parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """ Разбирает JSON-схему UML-диаграммы классов для Python """
        classes = data.get("classes", [])
        parsed_data = {"classes": []}

        for cls in classes:
            methods = []
            for method in cls.get("methods", []):
                params = [(param["name"], self.map_type(param["type"])) for param in method.get("params", [])]
                methods.append({
                    "name": method["name"],
                    "params": params,
                    "return_type": self.map_type(method.get("return_type", "None"))
                })

            parsed_data["classes"].append({
                "name": cls.get("name"),
                "attributes": [(attr["name"], self.map_type(attr.get("type", "Any"))) for attr in cls.get("attributes", [])],
                "methods": methods,
                "inherits": cls.get("inherits", None)
            })

        return parsed_data


class JavaClassGenerator(PythonClassGenerator):
    """ Генератор Java-классов """
    def map_type(self, type_name: str) -> str:
        """ Сопоставление типов Python -> Java """
        type_mappings = {
            "int": "int",
            "str": "String",
            "float": "float",
            "bool": "boolean",
            "Any": "Object",
            "None": "void"  # ВАЖНО: исправляем None -> void
        }
        if type_name.startswith("List["):
            inner_type = type_name[5:-1]
            return f"List<{self.map_type(inner_type)}>"
        return type_mappings.get(type_name, type_name)

    def parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """ Разбирает и сопоставляет типы для Java """
        parsed_data = super().parse_data(data)
        for cls in parsed_data["classes"]:
            cls["attributes"] = [(name, self.map_type(tp)) for name, tp in cls["attributes"]]
            for method in cls["methods"]:
                method["params"] = [(name, self.map_type(tp)) for name, tp in method["params"]]
                method["return_type"] = self.map_type(method["return_type"])
        return parsed_data


class CppClassGenerator(PythonClassGenerator):
    """ Генератор C++-классов """

    def map_type(self, type_name: str) -> str:
        """ Сопоставляет типы Python -> C++ """
        type_mappings = {
            "int": "int",
            "str": "std::string",
            "float": "float",
            "bool": "bool",
            "Any": "auto",
            "None": "void"  # ВАЖНО: исправляем None -> void
        }
        if type_name.startswith("List["):
            inner_type = type_name[5:-1]
            return f"std::vector<{self.map_type(inner_type)}>"
        return type_mappings.get(type_name, type_name)

    def parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """ Разбирает и сопоставляет типы для C++ """
        parsed_data = super().parse_data(data)
        for cls in parsed_data["classes"]:
            cls["attributes"] = [(name, self.map_type(tp)) for name, tp in cls["attributes"]]
            for method in cls["methods"]:
                method["params"] = [(name, self.map_type(tp)) for name, tp in method["params"]]
                method["return_type"] = self.map_type(method["return_type"])
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
    """ Определяет, какой генератор использовать: SQL, Классы (Python/Java/Cpp) или Docker Compose """
    with open(file_path, encoding="utf-8") as file:
        data = json.load(file)

    if "tables" in data:
        db_type = input("Выберите тип базы данных для генерации (mysql/oracle): ").strip().lower()
        if db_type == "mysql":
            return MySQLGenerator(file_path)
        elif db_type == "oracle":
            return OracleSQLGenerator(file_path)
        else:
            raise ValueError(f"Неизвестная база данных: {db_type}")
    elif "classes" in data:
        language = input("Выберите язык генерации (python/java/cpp): ").strip().lower()
        if language == "python":
            return PythonClassGenerator(file_path, "jinja_templates/classes_python.jinja2", "generated_code/classes.py")
        elif language == "java":
            return JavaClassGenerator(file_path, "jinja_templates/classes_java.jinja2", "generated_code/classes.java")
        elif language == "cpp":
            return CppClassGenerator(file_path, "jinja_templates/classes_cpp.jinja2", "generated_code/classes.cpp")
        else:
            raise ValueError(f"Неизвестный язык генерации: {language}")
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
