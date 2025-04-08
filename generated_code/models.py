
class Person:
    def __init__(self, name: str, age: int):
        
        
        self.name: str = name
        
        self.age: int = age
        

    
    def introduce(self) -> None:
        pass
    

class Student(Person):
    def __init__(self, name: str, age: int, student_id: str):
        
        super().__init__(name, age)
        
        
        self.student_id: str = student_id
        

    
    def enroll(self, course: Course) -> None:
        pass
    

class Professor(Person):
    def __init__(self, name: str, age: int, employee_id: str):
        
        super().__init__(name, age)
        
        
        self.employee_id: str = employee_id
        

    
    def teach(self, course: Course) -> None:
        pass
    

class Course:
    def __init__(self, course_name: str, students: List[Student], professor: Professor):
        
        
        self.course_name: str = course_name
        
        self.students: List[Student] = students
        
        self.professor: Professor = professor
        

    
    def add_student(self, student: Student) -> None:
        pass
    

class Department:
    def __init__(self, name: str, professors: List[Professor]):
        
        
        self.name: str = name
        
        self.professors: List[Professor] = professors
        

    
    def add_professor(self, professor: Professor) -> None:
        pass
    

class University:
    def __init__(self, name: str, departments: List[Department]):
        
        
        self.name: str = name
        
        self.departments: List[Department] = departments
        

    
    def add_department(self, department: Department) -> None:
        pass
    
