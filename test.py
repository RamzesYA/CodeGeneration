import re
import json
import sys
from typing import List, Dict, Any, Optional


class PlantUMLParser:
    def __init__(self):
        self.classes = []
        self.relationships = []
        self.current_class = None

    def parse_file(self, filename: str) -> Dict[str, Any]:
        """Основной метод парсинга файла"""
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
        """Парсинг содержимого PlantUML"""
        lines = content.split('\n')

        for line in lines:
            line = line.strip()

            # Пропускаем комментарии и пустые строки
            if not line or line.startswith("'") or line.startswith('@startuml') or line.startswith('@enduml'):
                continue

            # Парсинг классов
            if line.startswith('class '):
                self.parse_class(line)
            # Парсинг отношений
            elif any(relation in line for relation in ['<|--', '--', 'o--', '*--', '..>']):
                self.parse_relationship(line)
            # Парсинг содержимого класса (атрибуты и методы)
            elif line.startswith('{') or (self.current_class and ('}' not in line)):
                self.parse_class_content(line)

        return self.to_json()

    def parse_class(self, line: str):
        """Парсинг объявления класса"""
        # Извлекаем имя класса
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
        """Парсинг атрибутов и методов внутри класса"""
        if not self.current_class:
            return

        # Убираем фигурные скобки и лишние пробелы
        clean_line = re.sub(r'^\s*\{[^}]*\}\s*', '', line.strip())
        clean_line = clean_line.rstrip('}')

        if not clean_line or clean_line == '}':
            return

        # Парсинг атрибута
        attribute_match = re.match(r'^(-|\+)\s*(\w+)\s*:\s*([^()]+)$', clean_line)
        if attribute_match:
            visibility, name, data_type = attribute_match.groups()
            if visibility == '-':  # private атрибут
                self.current_class["attributes"].append({
                    "name": name.strip(),
                    "type": data_type.strip()
                })
            return

        # Парсинг метода
        method_match = re.match(r'^(\+|\-)\s*(\w+)\s*\((.*)\)\s*:\s*([^()]+)$', clean_line)
        if method_match:
            visibility, name, params_str, return_type = method_match.groups()
            if visibility == '+':  # public метод
                params = self.parse_method_params(params_str)
                self.current_class["methods"].append({
                    "name": name.strip(),
                    "return_type": return_type.strip(),
                    "params": params
                })

    def parse_method_params(self, params_str: str) -> List[Dict[str, str]]:
        """Парсинг параметров метода"""
        params = []
        if not params_str.strip():
            return params

        param_parts = params_str.split(',')
        for param in param_parts:
            param = param.strip()
            if ':' in param:
                name, param_type = param.split(':', 1)
                params.append({
                    "name": name.strip(),
                    "type": param_type.strip()
                })

        return params

    def parse_relationship(self, line: str):
        """Парсинг отношений между классами"""
        # Определяем тип отношения
        relationship_type = None
        multiplicity = "one-to-one"

        if '<|--' in line:
            relationship_type = "inheritance"
            # Для наследования определяем родителя и потомка
            parts = line.split('<|--')
            if len(parts) == 2:
                parent = self.clean_class_name(parts[0].strip())
                child = self.clean_class_name(parts[1].strip())
                # Обновляем наследование для класса-потомка
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

        # Для других типов отношений
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

        # Извлекаем классы и множественность
        pattern = r'\"([^\"]*)\"?\s*--\s*\"([^\"]*)\"?'
        match = re.search(pattern, line)

        if match:
            left_part, right_part = match.groups()

            # Извлекаем имена классов
            left_class = self.extract_class_name(left_part)
            right_class = self.extract_class_name(right_part)

            # Определяем множественность
            multiplicity = self.determine_multiplicity(left_part, right_part)

            self.relationships.append({
                "type": relationship_type,
                "from": left_class,
                "to": right_class,
                "multiplicity": multiplicity
            })

    def clean_class_name(self, class_name: str) -> str:
        """Очищает имя класса от лишних символов"""
        # Убираем кавычки и множественность
        return re.sub(r'[\"0-9.*]', '', class_name).strip()

    def extract_class_name(self, part: str) -> str:
        """Извлекает имя класса из части отношения"""
        # Убираем множественность и лишние символы
        return re.sub(r'[\"0-9.*]', '', part).strip()

    def determine_multiplicity(self, left: str, right: str) -> str:
        """Определяет тип множественности на основе обозначений"""
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
        """Парсит обозначение множественности"""
        if '0..*' in part or '1..*' in part or '*' in part:
            return "many"
        else:
            return "one"

    def to_json(self) -> Dict[str, Any]:
        """Возвращает результат в формате JSON"""
        return {
            "classes": self.classes,
            "relationships": self.relationships
        }


def save_to_json(data: Dict[str, Any], filename: str = "classes.json"):
    """Сохраняет данные в JSON файл"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Результат успешно сохранен в файл: {filename}")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сохранении файла: {e}")
        return False


def main():
    """Основная функция программы"""
    print("=== PlantUML to JSON Parser ===")
    print("Автоматическое сохранение в classes.json\n")

    # Запрашиваем имя файла у пользователя
    filename = input("Введите путь к файлу PlantUML: ").strip()

    if not filename:
        print("Ошибка: Не указано имя файла.")
        return

    # Создаем парсер и парсим файл
    parser = PlantUMLParser()
    result = parser.parse_file(filename)

    # Выводим результат в консоль
    print("\n=== Результат парсинга ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Автоматически сохраняем в classes.json
    print("\n=== Сохранение файла ===")
    save_to_json(result, "classes.json")

    # Дополнительная опция для сохранения под другим именем
    custom_save = input("\nХотите сохранить под другим именем? (y/n): ").strip().lower()
    if custom_save == 'y':
        custom_filename = input("Введите имя файла: ").strip()
        if custom_filename:
            save_to_json(result, custom_filename)


if __name__ == "__main__":
    main()