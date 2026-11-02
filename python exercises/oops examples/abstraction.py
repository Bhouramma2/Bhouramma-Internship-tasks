from abc import ABC, abstractmethod

class ATM(ABC):

    @abstractmethod
    def withdraw(self, amount):
        pass


class BankATM(ATM):

    def withdraw(self, amount):
        print(f"Successfully withdrawn: {amount}")


atm = BankATM()
atm.withdraw(500)
