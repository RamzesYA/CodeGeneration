from typing import List


class Book:
    def __init__(self, isbn: String, title: String, author: String, isAvailable: boolean):
        
        
        self.isbn: String = isbn
        
        self.title: String = title
        
        self.author: String = author
        
        self.isAvailable: boolean = isAvailable
        

    
    def borrow(self) -> 'void':
        pass
    
    def returnBook(self) -> 'void':
        pass
    

class Library:
    def __init__(self, name: String, address: String):
        
        
        self.name: String = name
        
        self.address: String = address
        

    
    def addBook(self, book: Book) -> 'void':
        pass
    
    def findBook(self, title: String) -> 'Book':
        pass
    
    def listAvailableBooks(self) -> 'List<Book>':
        pass
    

class Reader:
    def __init__(self, readerId: int, name: String, email: String):
        
        
        self.readerId: int = readerId
        
        self.name: String = name
        
        self.email: String = email
        

    
    def borrowBook(self, book: Book) -> 'boolean':
        pass
    
    def returnBook(self, book: Book) -> 'void':
        pass
    
