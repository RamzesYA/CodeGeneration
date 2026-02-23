import json
import re
import subprocess
from pathlib import Path
from typing import Dict, Any
from jinja2 import Template


class CodeValidator:
    """ Проверка сгенерированного кода для Python, Java и C++ """

    def __init__(self, language: str):
        self.language = language.lower()

    def validate(self, file_path: str):
        if self.language == "python":
            self._validate_python(file_path)
        elif self.language == "java":
            self._validate_java(file_path)
        elif self.language == "cpp":
            self._validate_cpp(file_path)
        else:
            print(f"⚠️ Валидация для языка '{self.language}' пока не поддерживается.")

    def _validate_python(self, file_path: str):
        print(f"🔍 Проверка Python кода: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            compile(source, file_path, "exec")
            print("✅ Python код успешно прошел проверку.\n")
        except SyntaxError as e:
            print(f"❌ Ошибка в Python коде:\n{e}\n")

    def _validate_java(self, file_path: str):
        print(f"🔍 Проверка Java кода: {file_path}")
        try:
            subprocess.run(["javac", file_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("✅ Java код успешно прошел проверку.\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка компиляции Java:\n{e.stderr.decode()}\n")
        except FileNotFoundError:
            print("❌ Компилятор Java (javac) не найден. Убедитесь, что он установлен и добавлен в PATH.\n")

    def _validate_cpp(self, file_path: str):
        print(f"🔍 Проверка C++ кода: {file_path}")
        try:
            subprocess.run(["g++", "-fsyntax-only", file_path], check=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
            print("✅ C++ код успешно прошел проверку.\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка компиляции C++:\n{e.stderr.decode()}\n")
        except FileNotFoundError:
            print("❌ Компилятор C++ (g++) не найден. Убедитесь, что он установлен и добавлен в PATH.\n")


class ClassDiagramValidator:
    """ Проверка корректности представления диаграммы классов (без проверки связей) """

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.class_names = {cls["name"] for cls in data.get("classes", [])}

    def validate(self) -> None:
        """ Проверяет корректность диаграммы классов """
        self._validate_classes()

    def _validate_classes(self) -> None:
        """ Проверяет корректность классов (наличие обязательных полей и правильность типов) """
        for cls in self.data.get("classes", []):
            self._validate_class(cls)

    def _validate_class(self, cls: Dict[str, Any]) -> None:
        """ Проверяет корректность одного класса """
        if not cls.get("name"):
            raise ValueError(f"Класс должен иметь имя. Проблема в классе: {cls}")

        if "attributes" not in cls or "methods" not in cls:
            raise ValueError(f"Класс {cls['name']} должен иметь поля 'attributes' и 'methods'.")

        # Проверка атрибутов
        for attr in cls.get("attributes", []):
            if "name" not in attr or "type" not in attr:
                raise ValueError(f"Атрибут {attr} в классе {cls['name']} должен иметь 'name' и 'type'.")

        # Проверка методов
        for method in cls.get("methods", []):
            if "name" not in method or "return_type" not in method:
                raise ValueError(f"Метод {method} в классе {cls['name']} должен иметь 'name' и 'return_type'.")

            for param in method.get("params", []):
                if "name" not in param or "type" not in param:
                    raise ValueError(f"Параметр {param} в методе {method['name']} должен иметь 'name' и 'type'.")


class DatabaseDiagramValidator:
    """Проверяет корректность представления диаграммы базы данных."""

    def __init__(self, diagram: dict):
        self.diagram = diagram

    def validate(self) -> None:
        """Запускает все проверки."""
        if "tables" not in self.diagram:
            raise ValueError("Диаграмма должна содержать ключ 'tables'.")

        if not isinstance(self.diagram["tables"], list):
            raise ValueError("'tables' должно быть списком.")

        for table in self.diagram["tables"]:
            self._validate_table(table)

        # сделаем только базовую проверку существования ключа:
        if "relationships" in self.diagram:
            if not isinstance(self.diagram["relationships"], list):
                raise ValueError("'relationships' должно быть списком.")

    def _validate_table(self, table: dict) -> None:
        """Проверяет корректность одной таблицы."""
        if "name" not in table:
            raise ValueError(f"Таблица должна иметь имя: {table}")

        if "columns" not in table:
            raise ValueError(f"Таблица {table['name']} должна содержать список 'columns'.")

        if not isinstance(table["columns"], list):
            raise ValueError(f"'columns' таблицы {table['name']} должно быть списком.")

        for column in table["columns"]:
            self._validate_column(column, table_name=table["name"])

    def _validate_column(self, column: dict, table_name: str) -> None:
        """Проверяет корректность одного столбца."""
        if "name" not in column or "type" not in column:
            raise ValueError(f"Каждый столбец в таблице {table_name} должен иметь 'name' и 'type'.")

        if "foreign_key" in column:
            foreign_key = column["foreign_key"]
            # Accept None, dict, or string shorthand like "Table.column"
            if foreign_key is None:
                return
            if isinstance(foreign_key, dict):
                if "references" not in foreign_key or "column" not in foreign_key:
                    raise ValueError(f"'foreign_key' в столбце {column['name']} таблицы {table_name} должен содержать 'references' и 'column'.")
                return
            if isinstance(foreign_key, str):
                # try to parse formats like "Table.column" or "Table(column)" or "Table:column"
                m = re.match(r"^(?P<table>[A-Za-z0-9_]+)[\.:(]?(?P<col>[A-Za-z0-9_]+)?\)?$", foreign_key.strip())
                if m and m.group('col'):
                    # normalize into dict for downstream code
                    column["foreign_key"] = {"references": m.group('table'), "column": m.group('col')}
                    return
                raise ValueError(f"'foreign_key' в столбце {column['name']} таблицы {table_name} должен быть словарём или строкой 'Table.column'.")
            raise ValueError(f"'foreign_key' в столбце {column['name']} таблицы {table_name} должен быть словарём, строкой или None.")


class DockerComposeDiagramValidator:
    """Проверяет корректность представления диаграммы Docker Compose."""

    def __init__(self, diagram: dict):
        self.diagram = diagram

    def validate(self) -> None:
        """Запускает все проверки."""
        if "nodes" not in self.diagram:
            raise ValueError("Диаграмма должна содержать ключ 'nodes'.")

        if not isinstance(self.diagram["nodes"], list):
            raise ValueError("'nodes' должно быть списком.")

        if any("name" not in node for node in self.diagram["nodes"]):
            raise ValueError("Каждый узел в 'nodes' должен иметь ключ 'name'.")

        node_names = {node["name"] for node in self.diagram["nodes"]}

        if "connections" in self.diagram:
            if not isinstance(self.diagram["connections"], list):
                raise ValueError("'connections' должно быть списком.")
            for connection in self.diagram["connections"]:
                self._validate_connection(connection, node_names)

    def _validate_connection(self, connection: dict, node_names: set) -> None:
        """Проверяет корректность одного соединения."""
        required_keys = {"from", "to", "label"}
        if not required_keys.issubset(connection.keys()):
            raise ValueError(f"Соединение должно содержать ключи {required_keys}: {connection}")

        if connection["from"] not in node_names:
            raise ValueError(f"Узел-источник '{connection['from']}' не найден в 'nodes'.")

        if connection["to"] not in node_names:
            raise ValueError(f"Узел-получатель '{connection['to']}' не найден в 'nodes'.")


class Generator:
    """ Базовый класс генератора """

    def __init__(self, file_path: str, template_file: str, output_file: str, language: str = None, validate_code: bool = True):
        self.file_path = Path(file_path)
        self.template_file = Path(template_file)
        self.output_file = Path(output_file)
        self.language = language  # Новый параметр для понимания типа кода
        self.validate_code = validate_code  # Флаг для включения/выключения валидации

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

        if self.validate_code:
            if self.language:
                validator = CodeValidator(self.language)
                validator.validate(str(self.output_file))


class SQLGenerator(Generator):
    """ Генератор SQL-кода для Postgesql """

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
    def __init__(self, file_path: str, template_file: str, output_file: str, language: str, validate_code: bool = False):
        super().__init__(file_path, template_file, output_file, language, validate_code)

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
        validator = DatabaseDiagramValidator(data)
        validator.validate()
        db_type = input("Выберите тип базы данных для генерации (postgresql/mysql/oracle): ").strip().lower()
        if db_type == "postgresql":
            return SQLGenerator(file_path, "jinja_templates/postgresql_template.jinja2", "generated_sql/postgresql_db.sql")
        elif db_type == "mysql":
            return MySQLGenerator(file_path)
        elif db_type == "oracle":
            return OracleSQLGenerator(file_path)
        else:
            raise ValueError(f"Неизвестная база данных: {db_type}")
    elif "classes" in data:
        validator = ClassDiagramValidator(data)
        validator.validate()
        validate_code_input = input("Хотите ли вы выполнить проверку сгенерированного кода? (y/n): ").strip().lower()
        validate_code = validate_code_input == "y"
        language = input("Выберите язык генерации (python/java/cpp): ").strip().lower()
        if language == "python":
            return PythonClassGenerator(file_path, "jinja_templates/classes_python.jinja2", "generated_code/classes.py", language=language, validate_code=validate_code)
        elif language == "java":
            return JavaClassGenerator(file_path, "jinja_templates/classes_java.jinja2", "generated_code/classes.java", language=language, validate_code=validate_code)
        elif language == "cpp":
            return CppClassGenerator(file_path, "jinja_templates/classes_cpp.jinja2", "generated_code/classes.cpp", language=language, validate_code=validate_code)
        else:
            raise ValueError(f"Неизвестный язык генерации: {language}")
    elif "nodes" in data and "connections" in data:
        validator = DockerComposeDiagramValidator(data)
        validator.validate()
        return DockerComposeGenerator(file_path, "jinja_templates/docker_compose.jinja2", "generated_code/docker-compose.yaml")
    else:
        raise ValueError("Неизвестный формат JSON. Ожидаются ключи 'tables', 'classes' или 'nodes'.")


def detect_generator_from_data(data: dict, *, prefer_language: str = None, validate_code: bool = False, db_type: str = None) -> Generator:
    """Non-interactive generator selector from parsed JSON data.

    prefer_language: for classes -> 'python'|'java'|'cpp'
    db_type: for database -> 'postgresql'|'mysql'|'oracle'
    """
    if "tables" in data:
        validator = DatabaseDiagramValidator(data)
        validator.validate()
        if db_type is None:
            db_type = "postgresql"
        if db_type == "postgresql":
            return SQLGenerator("<in-memory>", "jinja_templates/postgresql_template.jinja2", "generated_sql/postgresql_db.sql")
        elif db_type == "mysql":
            return MySQLGenerator("<in-memory>")
        elif db_type == "oracle":
            return OracleSQLGenerator("<in-memory>")
        else:
            raise ValueError(f"Неизвестная база данных: {db_type}")
    elif "classes" in data:
        validator = ClassDiagramValidator(data)
        validator.validate()
        language = (prefer_language or "python").lower()
        if language == "python":
            return PythonClassGenerator("<in-memory>", "jinja_templates/classes_python.jinja2", "generated_code/classes.py", language=language, validate_code=validate_code)
        elif language == "java":
            return JavaClassGenerator("<in-memory>", "jinja_templates/classes_java.jinja2", "generated_code/classes.java", language=language, validate_code=validate_code)
        elif language == "cpp":
            return CppClassGenerator("<in-memory>", "jinja_templates/classes_cpp.jinja2", "generated_code/classes.cpp", language=language, validate_code=validate_code)
        else:
            raise ValueError(f"Неизвестный язык генерации: {language}")
    elif "nodes" in data and "connections" in data:
        validator = DockerComposeDiagramValidator(data)
        validator.validate()
        return DockerComposeGenerator("<in-memory>", "jinja_templates/docker_compose.jinja2", "generated_code/docker-compose.yaml")
    else:
        raise ValueError("Неизвестный формат данных для генерации")


if __name__ == "__main__":
    file_path = "json_templates/classes.json"  # Укажите путь к JSON-файлу
    try:
        generator = detect_generator(file_path)
        generator.generate()
    except Exception as e:
        print("Ошибка:", e)
