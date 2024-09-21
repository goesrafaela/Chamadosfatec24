import os

# Gera uma chave secreta de 24 bytes aleatórios
secret_key = os.urandom(24)
# Exibe a chave gerada no terminal
print(secret_key.hex())
