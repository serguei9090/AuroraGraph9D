# Software Engineering: Design Patterns and Architecture

## Creational Patterns

### Singleton Pattern
The Singleton pattern ensures a class has only one instance and provides a global access point to it. In Python, this is commonly implemented using the __new__ method or a metaclass. The pattern was first formally described by the Gang of Four (Gamma, Helm, Johnson, and Vlissides) in their 1994 book "Design Patterns: Elements of Reusable Object-Oriented Software", published by Addison-Wesley with ISBN 0-201-63361-2.

Thread-safe Singleton implementation requires double-checked locking. In Java, this uses the volatile keyword along with synchronized blocks. The performance overhead of synchronized access is approximately 15-25% compared to unsynchronized access.

### Factory Method Pattern
The Factory Method defines an interface for creating objects but lets subclasses decide which class to instantiate. A real-world example: a document application might define a createDocument() factory method returns different Document subclasses (WordDocument, PDFDocument, SpreadsheetDocument) depending on the file extension.

The Factory pattern reduces coupling by eliminating the need to bind application-specific classes into the code. According to Robert C. Martin's SOLID principles, this follows the Dependency Inversion Principle (DIP): depend upon abstractions, not concretions.

## Structural Patterns

### Observer Pattern
The Observer pattern defines a one-to-many dependency between objects. When one object (the Subject) changes state, all its dependents (Observers) are notified automatically. This pattern is the foundation of the Model-View-Controller (MVC) architecture, first implemented at Xerox PARC in 1978 by Trygve Reenskaug.

In JavaScript, the addEventListener method is a direct implementation of the Observer pattern. The maximum number of listeners recommended by Node.js per EventEmitter is 10 by default, controlled by the maxListeners property. Exceeding this limit triggers a warning: "MaxListenersExceededWarning".

### Decorator Pattern
The Decorator pattern attaches additional responsibilities to an object dynamically. Python uses the @decorator syntax (introduced in PEP 318, accepted on September 2, 2004). A decorated function in Python retains its original function's metadata when functools.wraps is applied.

## Architecture Patterns

### Microservices vs Monolith
Netflix migrated from a monolithic architecture to microservices starting in 2009, completing the migration in 2012. Their system grew from a single monolith to over 700 microservices. The key metrics reported after migration: deployment frequency increased from weekly to thousands per day, and system availability improved from 99.7% to 99.99%.

### REST API Standards
REST (Representational State Transfer) was defined by Roy Fielding in his 2000 doctoral dissertation at UC Irvine. The six constraints of REST are: Client-Server, Stateless, Cacheable, Uniform Interface, Layered System, and Code-on-Demand (optional). HTTP status codes follow specific ranges: 2xx for success, 3xx for redirection, 4xx for client errors, and 5xx for server errors. Status code 418 "I'm a teapot" was defined in RFC 2324 as an April Fools' joke in 1998.

### Database Indexing
A B-tree index with a branching factor of 500 can store 500 million keys in just 3 levels of the tree. PostgreSQL uses B-tree as its default index type. The time complexity of a B-tree search is O(log n), and for a table with 10 million rows, a B-tree index lookup typically requires 3-4 disk reads compared to a full table scan of potentially millions of reads.
