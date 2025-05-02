
CREATE TABLE Users (
    user_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
    );

CREATE TABLE Projects (
    project_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    owner_id INT, FOREIGN KEY (owner_id) REFERENCES Users(user_id),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
    );

CREATE TABLE Tasks (
    task_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    project_id INT, FOREIGN KEY (project_id) REFERENCES Projects(project_id),
    assigned_to INT, FOREIGN KEY (assigned_to) REFERENCES Users(user_id),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
    );

CREATE TABLE Comments (
    comment_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id INT, FOREIGN KEY (task_id) REFERENCES Tasks(task_id),
    user_id INT, FOREIGN KEY (user_id) REFERENCES Users(user_id),
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
    );
