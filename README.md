# MiniStore-API

Projeto de **aprendizado em Django REST Framework (DRF)**: uma **API RESTful de e-commerce** em desenvolvimento.  
O objetivo é praticar **CRUD de produtos, criação e visualização de pedidos**, autenticação de usuários e boas práticas de backend, registrando minha **evolução durante o desenvolvimento**.

> **Atenção:** Projeto ainda em desenvolvimento. Funcionalidades podem mudar e novas serão adicionadas.

---

## Tecnologias Utilizadas

- Python  
- Django  
- Django REST Framework  
- SQLite

---

## Funcionalidades Implementadas

    - CRUD de Produtos: criar, listar, atualizar e deletar produtos.  
    - Autenticação de Usuários: registro e login com token de autenticação.  
    - Criação de Pedidos: usuários autenticados podem criar pedidos com produtos.  
    - Listagem de Pedidos: usuários podem ver os pedidos que criaram.  
    - Permissões básicas: apenas usuários autenticados podem criar pedidos; usuários só acessam seus próprios pedidos.  
    - Estrutura organizada em Django e DRF: separação clara de models, serializers e views; endpoints RESTful padronizados.


Cada funcionalidade representa um passo do meu aprendizado em Django e DRF.

---

## Evolução do Projeto

1. **Início**  
   - Criação de endpoints básicos para produtos.
   - Implementação do model de produtos com campos essenciais (nome, descrição, preço, estoque).  

2. **Intermediário**  
   - Implementação da autenticação de usuários via DRF (registro e login com token).  
   - Proteção de endpoints.

3. **Atual**  
   - Desenvolvimento da funcionalidade de pedidos: criação e listagem para usuários autenticados.  
   - Controle de permissões.
   - Organização do projeto com views, serializers e URLs estruturadas.  

4. **Futuro**  
   - Adição de novas funcionalidades relacionadas a pedidos e produtos.  
   - Implementação de testes automatizados para a API.  
   - Otimização e refinamento do código, seguindo boas práticas de backend.


---

## Autor

- Bruno Vinicius Nascimento Lima — [GitHub](https://github.com/bn-lima)
