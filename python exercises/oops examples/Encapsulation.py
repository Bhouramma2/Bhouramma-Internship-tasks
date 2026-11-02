class BankAccount:
    def __init__(self, balance):
        self.__balance = balance

    def deposit(self, amount):
        self.__balance += amount
        print(f"Deposited: {amount}. New Balance: {self.__balance}")

    def get_balance(self):
        return self.__balance


account = BankAccount(1000)
account.deposit(500)

print("Current Balance:", account.get_balance())