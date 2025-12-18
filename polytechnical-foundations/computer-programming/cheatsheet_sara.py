'''WEEK 1: INTRODUCTION'''
x = 10
abs(-7) # Absolute value
round(3.14159, 2) # Round to 2 decimal place
type(x)  # Type checking
sep='-' # Seperate using -
end='0' # End with 0


'''WEEK 2: VARIABLES AND DATA TYPES'''
import math

x_float = float(10) # Convert to float
x_str = str(10) # Convert to string
x_int = int(10.5) # Convert to int

modulus = 10 % 3 #the remainder of the division
div = 10 // 3 #the integer of the division

max(5, 10) # Maximum value of the two
min(5, 10) # Minimum value of the two

math.sin(60) # Sine function
math.cos(60) # Cosine function
math.pow(2, 3) # 2 to the power of 3
math.exp(2) # e to the of 2
math.log(10) # Natural logarithm
math.sqrt(16) # Square root
math.ceil(2.1) # Round up
math.floor(2.9) # Round down
math.pi
math.fabs(-10) # Absolute value
math.fsum([1, 2, 3]) # Sum of the list

True # = 1
False # = 0
''' and -> True if both are True, else False
    or -> True if either is True, else False
    not -> True if False, else False        '''


'''WEEK 3: CONDITIONALS'''
# if , elif, else
''' == equal
    != not equal
    < less than
    > greater than
    <= less than or equal to
    >= greater than or equal to '''


'''WEEK 4: LOOPS'''
# for
''' in range(5) -> 0, 1, 2, 3, 4
    in range(1, 5) -> 1, 2, 3, 4
    in range(1, 10, 2) -> start, stop, step '''
# while
''' while condition -> loop until condition is False '''
# break -> exit the loop

'''WEEK 5: FUNCTIONS'''
def add_numbers(a, b): # name(variables)
    print(f"Adding {a} and {b}")
    return a + b

print("Sum:", add_numbers(2, 3)) # call the function


'''WEEK 6: LISTS'''
n = range(3)
lst = list(n) # Convert range to list 0-2

len(lst)  # Length of the list
sum(lst)  # Sum of the list
min(lst)  # Minimum value
max(lst)  # Maximum value
any(lst)  # if any element is True
all(lst)  # if all elements are True

lst.sort()  # Sort the list ascending/alphabetical order
lst.append(99)  # Takes only one argument
lst.extend([4, 5])  # Takes multiple arguments
lst.pop(1)   # Remove by index
lst[::-1] # Reverse the list
lst.count(2)  # Count occurrences
lst.index(3)  # Find index if nothing returns -1
lst2 = lst.copy()  # Copy the list
lst.remove(100)  # Remove by value

nested_list = [[1, 2], [3, 4]]
nested_list[0][1] # Access nested list element

squared = [x**2 for x in range(5)] # Makes a list 0-4 ** 2

names = ["Anne-marie", "Benjamin", "Cirkeline"]
ages = [25, 30, 35]
occupations = ["Engineer", "Doctor", "Artist"]
for name, age, occupation in zip(names, ages, occupations): # Loop over multiple lists with same length
    print(f"{name} is {age} years old and works as a {occupation}")

'''NOT SURE YOU ARE ALLOWED TO USE THIS'''
rev = list(reversed(lst))
lst.reverse()


'''WEEK 7: STRINGS'''
string = "Hello, World!"

string.lower()
string.upper()
string.find("World") # Returns index if not returns -1
string.index("World") # Returns index
string.count("l") # Count occurrences
string.split("-") # split in parts divided by -, you can access the first part by string.split("-")[0]
string.replace("World", "Alice") # Replace substring
string.strip() # Remove whitespace

words = "split this sentence".split()
string.split(" ", 2) # Split by whitespace, max 2 splits
string = " ".join(words) # Join list of strings

print("Tabbed text:\tExample") # Tab
print("Newline:\nExample") # Newline
print("Backslash:\\Example") # Backslash
print("Quote:\"Example\"") # Quote

repr("Hello\nWorld") # Display with escape sequences

f"{216:5d}" # Spaces-padded
f"{216:05d}" # Zero-padded
f"{3.14159:.2f}" # Two decimal places
f"{3.14159:08.2f}" # Zero-padded and two decimal places

string[::-1] # Reverse string
string[2:5] # Slice string


'''WEEK 8: DICTIONARIES AND TUPLES'''
numbers = dict(x=1, y=2, z=3) # Create dictionary
person = {"first_name": "Alice", "last_name": "Baker", "age": 34}

person["age"] # Access value
del person['last_name'] # Delete key-value pair
person.keys() # Get keys
person.values() # Get values
person.items() # Get key-value pairs

for key in person: # Going over keys
    print(key)
for value in person: # Going over values
    print(person[value])

(1, 2, 3) # Tuple
first, second, third = 1, 2, 3 # Also tuple
'''slicing, indexing and going over a tuple same as list'''


'''WEEK 9: FILES'''
import os
cwd = os.getcwd() # Current working directory

file_path = os.path.join(cwd, "data.txt") # Join the cwd path and data.txt
os.listdir() # List files in the directory
os.path.isfile(file_path) # Check if file exists
os.path.isdir(cwd) # Check if directory exists

with open(file_path, "r") as file: # Reading from a file
    content = file.read()
    lines = file.readline() # List of lines (all ending with \n) from a file 
    file.close() # Close the file

for line in lines:
    print(line.strip()) # Strip whitespace

content.splitlines() # Split by lines

with open(file_path, "w") as file:  # Writing in a file
    file.write("Hello, World!\n")
    file.writelines(lines) # Write multiple lines


'''WEEK 10: CLASSES I'''
class Person:
    def __init__(self, name, age): # Constructor
        self.name = name
        self.age = age

    def introduce(self):
        return f"Hi, I'm {self.name} and I'm {self.age} years old."

person = Person("Alice", 30) # Object creation
person.introduce() # Method call
person.age = 31 # Attribute change


'''WEEK 11: CLASSES II'''
class Animal:
    def __init__(self, species, name=None):
        self.species = species
        self.name = name

    def make_sound(self):
        return "Some generic sound"

    def __str__(self):
        return f"{self.name or 'An animal'} the {self.species}"
    
    def __eq__(self, other):
        return self.species == other.species
    
    def __add__(self, other):
        return Animal("Mutant", f"{self.name} + {other.name}")

class Dog(Animal): # Dog is a subclass of Animal
    def __init__(self, name):
        super().__init__("Dog")  # Call the parent class's __init__
        self.name = name

    def make_sound(self):
        return f"{self.name} says Woof!"

dog = Dog("Buddy")
another = Dog("Max")
print(dog.species)  # Output: Dog
print(dog.make_sound())  # Output: Buddy says Woof!
dog == another # Output: True


'''WEEK 12: NUMPY'''
import numpy as np
import matplotlib.pyplot as plt

array1 = np.array([1, 2, 3])
array2 = np.array([4, 5, 6])
d = [1, 2, 3,
     4, 5, 6]

array1.astype(float) # Convert to float
array1.size # Number of elements

sum = array1 + array2 # Element-wise addition
''' * -> Element-wise multiplication
    / -> Element-wise division
    // -> Element-wise floor division
    ** -> Element-wise power
    % -> Element-wise modulus        '''

np.arange(1, 10, 2) # Array from 1 to 10 with step 2
np.linspace(1, 10, 5) # Array from 1 to 10 with 5 elements
np.zeros(3) # Array of zeros
np.ones(3) # Array of ones
np.empty(3) # Array of random values


np.log(array1) # Natural logarithm
np.sqrt(array1) # Square root
np.exp(array1) # Exponential
np.sin(array1) # Sine function
np.abs(array1) # Absolute value

np.sum(array1) # Sum of the array
np.mean(array1) # Mean of the array
np.std(array1) # Standard deviation
np.dot(array1, array2) # Dot product
np.unique(array1, counts=True) # Unique values and their counts
cpy = array1.copy() # Copy the array

d.size() # Number of elements
d.shape() # Shape of the array
d.shape[0] # Number of rows
d.shape[1] # Number of columns
d.ndim() # Number of dimensions
d.sum(axis=0) # column-wise sum
d.sum(axis=1) # row-wise sum
d.argmax(axis=1) # Index of the maximum value in each row
d.argmin() # Index of the minimum value


