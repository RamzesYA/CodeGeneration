
CREATE TABLE `Users` (
    `user_id` INT  PRIMARY KEY   ,
     `username` VARCHAR(50)    ,
     `email` VARCHAR(100)    ,
     `created_at` DATETIME      
) ENGINE=InnoDB;

CREATE TABLE `Posts` (
    `post_id` INT  PRIMARY KEY   ,
     `user_id` INT    ,
     `title` VARCHAR(200)    ,
     `content` TEXT    ,
     `created_at` DATETIME    ,
     `updated_at` DATETIME      ,
    FOREIGN KEY (`user_id`) REFERENCES `Users`(`user_id`)
    
    
) ENGINE=InnoDB;

CREATE TABLE `Comments` (
    `comment_id` INT  PRIMARY KEY   ,
     `post_id` INT    ,
     `user_id` INT    ,
     `comment_text` TEXT    ,
     `created_at` DATETIME      ,
    FOREIGN KEY (`post_id`) REFERENCES `Posts`(`post_id`),
    FOREIGN KEY (`user_id`) REFERENCES `Users`(`user_id`)
    
    
) ENGINE=InnoDB;
