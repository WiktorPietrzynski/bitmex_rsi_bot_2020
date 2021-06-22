import sys
def main():
    print("")
    name=str(input("Podaj nazwę pliku: "))
    if name=="exit()":
        print("Wyjście")
        sys.exit()
    else:
        try:
            file = open(name, "r")
            content = file.read()
            print(content)
        except:
            print("")
            print("Brak pliku. Spróbuj ponownie")
            main()
main()



