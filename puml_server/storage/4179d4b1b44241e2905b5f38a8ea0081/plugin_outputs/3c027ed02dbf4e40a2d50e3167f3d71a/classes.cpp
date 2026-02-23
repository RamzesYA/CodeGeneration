#include <string>
#include <vector>

class Book;
class Library;
class Reader;


class Book {
public:
    void borrow();
    void returnBook();
private:String isbn;
    String title;
    String author;
    boolean isAvailable;
    };

class Library {
public:
    void addBook(Book book);
    Book findBook(String title);
    List<Book> listAvailableBooks();
private:String name;
    String address;
    };

class Reader {
public:
    boolean borrowBook(Book book);
    void returnBook(Book book);
private:int readerId;
    String name;
    String email;
    };
