# Instructions pour les contributeurs

- Pour toute modification de code Python, vérifiez qu'il n'y a pas d'erreur de syntaxe en exécutant :
  ```bash
  python -m py_compile $(git ls-files '*.py')
  ```
- Les dépendances sont listées dans `requirements.txt`.
- Les clés d'accès (Supabase, Google) doivent être fournies via `secrets.toml` ou des variables d'environnement et **ne doivent pas être commitées**.
