
CREATE TABLE Users (
    user_id INT PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(100),
    created_at DATETIME
    );

CREATE TABLE Posts (
    post_id INT PRIMARY KEY,
    user_id INT, FOREIGN KEY (user_id) REFERENCES Users(user_id),
    title VARCHAR(200),
    content TEXT,
    created_at DATETIME,
    updated_at DATETIME
    );

CREATE TABLE Comments (
    comment_id INT PRIMARY KEY,
    post_id INT, FOREIGN KEY (post_id) REFERENCES Posts(post_id),
    user_id INT, FOREIGN KEY (user_id) REFERENCES Users(user_id),
    comment_text TEXT,
    created_at DATETIME
    );
