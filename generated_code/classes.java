import java.util.List;


public class User {
    
    private int id;
    
    private String username;
    
    private String email;
    

    
    public Task create_task(String title, Project project) {
        // TODO: Implement
        return null;
    }
    
}

public class Project {
    
    private int id;
    
    private String name;
    
    private User owner;
    
    private List<User> members;
    

    
    public void add_member(User user) {
        // TODO: Implement
        
    }
    
    public Task create_task(String title, User creator) {
        // TODO: Implement
        return null;
    }
    
}

public class Task {
    
    private int id;
    
    private String title;
    
    private String description;
    
    private String status;
    
    private User assignee;
    
    private Project project;
    
    private List<Comment> comments;
    

    
    public void change_status(String new_status) {
        // TODO: Implement
        
    }
    
    public void assign_to(User user) {
        // TODO: Implement
        
    }
    
}

public class Comment {
    
    private int id;
    
    private String content;
    
    private User author;
    
    private Task task;
    

    
    public void edit(String new_content) {
        // TODO: Implement
        
    }
    
}
