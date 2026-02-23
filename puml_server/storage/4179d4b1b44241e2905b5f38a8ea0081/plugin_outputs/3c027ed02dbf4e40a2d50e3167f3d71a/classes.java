import java.util.List;

public class Main {
    
    public static class Book {
        private String isbn;
        private String title;
        private String author;
        private boolean isAvailable;
        
        public void borrow() {
            }
        public void returnBook() {
            }
        }
    
    public static class Library {
        private String name;
        private String address;
        
        public void addBook(Book book) {
            }
        public Book findBook(String title) {
            return null;}
        public List<Book> listAvailableBooks() {
            return null;}
        }
    
    public static class Reader {
        private int readerId;
        private String name;
        private String email;
        
        public boolean borrowBook(Book book) {
            return null;}
        public void returnBook(Book book) {
            }
        }
    
  public static void main(String[] args) {
	}
}