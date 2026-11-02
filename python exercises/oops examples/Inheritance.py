
class Parent:
    def house(self):
        print("Parent owns a house")

class Child(Parent):
    def car(self):
        print("Child owns a car")

c = Child()
c.house()
c.car()
