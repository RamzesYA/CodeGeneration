
CREATE TABLE Users (
    user_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(100) NOT NULL ENABLE,
    email VARCHAR(255) NOT NULL ENABLE,
    password_hash VARCHAR(255) NOT NULL ENABLE,
    created_at TIMESTAMP NOT NULL ENABLE,
    updated_at TIMESTAMP NOT NULL ENABLE
);

CREATE TABLE Projects (
    project_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL ENABLE,
    description CLOB NOT NULL ENABLE,
    owner_id INT,
    created_at TIMESTAMP NOT NULL ENABLE,
    updated_at TIMESTAMP NOT NULL ENABLE,
    FOREIGN KEY (owner_id) REFERENCES Users(user_id)
);

CREATE TABLE Tasks (
    task_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(255) NOT NULL ENABLE,
    description CLOB NOT NULL ENABLE,
    status VARCHAR(50) NOT NULL ENABLE,
    priority VARCHAR(50) NOT NULL ENABLE,
    project_id INT,
    assigned_to INT,
    created_at TIMESTAMP NOT NULL ENABLE,
    updated_at TIMESTAMP NOT NULL ENABLE,
    FOREIGN KEY (project_id) REFERENCES Projects(project_id),
    FOREIGN KEY (assigned_to) REFERENCES Users(user_id)
);

CREATE TABLE Comments (
    comment_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id INT,
    user_id INT,
    content CLOB NOT NULL ENABLE,
    created_at TIMESTAMP NOT NULL ENABLE,
    FOREIGN KEY (task_id) REFERENCES Tasks(task_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);
