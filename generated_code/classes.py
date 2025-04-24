from typing import List


class User:
    def __init__(self, id: int, username: str, email: str):
        
        
        self.id: int = id
        
        self.username: str = username
        
        self.email: str = email
        

    
    def create_task(self, title: str, project: Project) -> 'Task':
        pass
    

class Project:
    def __init__(self, id: int, name: str, owner: User, members: List[User]):
        
        
        self.id: int = id
        
        self.name: str = name
        
        self.owner: User = owner
        
        self.members: List[User] = members
        

    
    def add_member(self, user: User) -> None:
        pass
    
    def create_task(self, title: str, creator: User) -> 'Task':
        pass
    

class Task:
    def __init__(self, id: int, title: str, description: str, status: str, assignee: User, project: Project, comments: List[Comment]):
        
        
        self.id: int = id
        
        self.title: str = title
        
        self.description: str = description
        
        self.status: str = status
        
        self.assignee: User = assignee
        
        self.project: Project = project
        
        self.comments: List[Comment] = comments
        

    
    def change_status(self, new_status: str) -> None:
        pass
    
    def assign_to(self, user: User) -> None:
        pass
    

class Comment:
    def __init__(self, id: int, content: str, author: User, task: Task):
        
        
        self.id: int = id
        
        self.content: str = content
        
        self.author: User = author
        
        self.task: Task = task
        

    
    def edit(self, new_content: str) -> None:
        pass
    
