#include <string>
#include <vector>

class User;
class Project;
class Task;
class Comment;


class User {
public:
    Task create_task(std::string title, Project project);
private:int id;
    std::string username;
    std::string email;
    };

class Project {
public:
    void add_member(User user);
    Task create_task(std::string title, User creator);
private:int id;
    std::string name;
    User owner;
    std::vector<User> members;
    };

class Task {
public:
    void change_status(std::string new_status);
    void assign_to(User user);
private:int id;
    std::string title;
    std::string description;
    std::string status;
    User assignee;
    Project project;
    std::vector<Comment> comments;
    };

class Comment {
public:
    void edit(std::string new_content);
private:int id;
    std::string content;
    User author;
    Task task;
    };
