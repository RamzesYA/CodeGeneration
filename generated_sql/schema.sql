
CREATE TABLE Students (
    
    student_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    
    name VARCHAR(100) NOT NULL,
    
    age INT NOT NULL,
    
    department_id INT, FOREIGN KEY (department_id) REFERENCES Departments(department_id)
    
);

CREATE TABLE Professors (
    
    professor_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    
    name VARCHAR(100) NOT NULL,
    
    age INT NOT NULL,
    
    department_id INT, FOREIGN KEY (department_id) REFERENCES Departments(department_id)
    
);

CREATE TABLE Courses (
    
    course_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    
    course_name VARCHAR(100) NOT NULL,
    
    professor_id INT, FOREIGN KEY (professor_id) REFERENCES Professors(professor_id)
    
);

CREATE TABLE Departments (
    
    department_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    
    name VARCHAR(100) NOT NULL
    
);

CREATE TABLE Enrollments (
    
    student_id INT PRIMARY KEY, FOREIGN KEY (student_id) REFERENCES Students(student_id),
    
    course_id INT PRIMARY KEY, FOREIGN KEY (course_id) REFERENCES Courses(course_id),
    
    enrollment_date DATE NOT NULL
    
);
