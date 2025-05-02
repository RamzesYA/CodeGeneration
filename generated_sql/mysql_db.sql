
CREATE TABLE `Users` (
    `user_id` INT  PRIMARY KEY  AUTO_INCREMENT  ,
     `username` VARCHAR(100)    NOT NULL ,
     `email` VARCHAR(255)    NOT NULL ,
     `password_hash` VARCHAR(255)    NOT NULL ,
     `created_at` TIMESTAMP    NOT NULL ,
     `updated_at` TIMESTAMP    NOT NULL   
) ENGINE=InnoDB;

CREATE TABLE `Projects` (
    `project_id` INT  PRIMARY KEY  AUTO_INCREMENT  ,
     `name` VARCHAR(100)    NOT NULL ,
     `description` TEXT    NOT NULL ,
     `owner_id` INT    ,
     `created_at` TIMESTAMP    NOT NULL ,
     `updated_at` TIMESTAMP    NOT NULL   ,
    FOREIGN KEY (`owner_id`) REFERENCES `Users`(`user_id`)
    
    
) ENGINE=InnoDB;

CREATE TABLE `Tasks` (
    `task_id` INT  PRIMARY KEY  AUTO_INCREMENT  ,
     `title` VARCHAR(255)    NOT NULL ,
     `description` TEXT    NOT NULL ,
     `status` VARCHAR(50)    NOT NULL ,
     `priority` VARCHAR(50)    NOT NULL ,
     `project_id` INT    ,
     `assigned_to` INT    ,
     `created_at` TIMESTAMP    NOT NULL ,
     `updated_at` TIMESTAMP    NOT NULL   ,
    FOREIGN KEY (`project_id`) REFERENCES `Projects`(`project_id`),
    FOREIGN KEY (`assigned_to`) REFERENCES `Users`(`user_id`)
    
    
) ENGINE=InnoDB;

CREATE TABLE `Comments` (
    `comment_id` INT  PRIMARY KEY  AUTO_INCREMENT  ,
     `task_id` INT    ,
     `user_id` INT    ,
     `content` TEXT    NOT NULL ,
     `created_at` TIMESTAMP    NOT NULL   ,
    FOREIGN KEY (`task_id`) REFERENCES `Tasks`(`task_id`),
    FOREIGN KEY (`user_id`) REFERENCES `Users`(`user_id`)
    
    
) ENGINE=InnoDB;
