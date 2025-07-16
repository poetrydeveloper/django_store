import os
import ast
import re
import hashlib
import logging
import argparse
from datetime import datetime
from collections import defaultdict
EXCLUDE_DIRS = {'migrations', '__pycache__', 'venv', '.git', 'scripts'}

try:
    import git
except ImportError:
    print("Модуль 'git' не найден. Установите его с помощью:\n\n    pip install GitPython\n")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)


class AdvancedDjangoAnalyzer:
    def __init__(self, project_root):
        self.project_root = project_root
        self.output_dir = os.path.join(project_root, "docs", "mermaid")
        self.file_hashes = {}
        self.import_graph = defaultdict(set)
        self.template_graph = defaultdict(set)
        self.repo = self.init_git_repo()
        self.load_hashes()

    def init_git_repo(self):
        try:
            return git.Repo(self.project_root)
        except Exception as e:
            logging.warning(f"Git репозиторий не найден или ошибка при инициализации: {e}")
            return None

    def load_hashes(self):
        hash_file = os.path.join(self.output_dir, "file_hashes.txt")
        if os.path.exists(hash_file):
            try:
                with open(hash_file, 'r') as f:
                    for line in f:
                        path, hash_val = line.strip().split('|')
                        self.file_hashes[path] = hash_val
            except Exception as e:
                logging.error(f"Ошибка при загрузке хешей: {e}")

    def save_hashes(self):
        os.makedirs(self.output_dir, exist_ok=True)
        try:
            with open(os.path.join(self.output_dir, "file_hashes.txt"), 'w') as f:
                for path, hash_val in self.file_hashes.items():
                    f.write(f"{path}|{hash_val}\n")
        except Exception as e:
            logging.error(f"Ошибка при сохранении хешей: {e}")

    def get_file_status(self, file_path):
        rel_path = os.path.relpath(file_path, self.project_root)
        current_hash = self.calculate_file_hash(file_path)

        status = None
        if rel_path not in self.file_hashes:
            status = "new"
        elif self.file_hashes[rel_path] != current_hash:
            status = "changed"

        self.file_hashes[rel_path] = current_hash

        if self.repo:
            git_status = self.get_git_file_status(rel_path)
            if git_status:
                status = git_status

        return status

    def get_git_file_status(self, rel_path):
        try:
            changed = [item.a_path for item in self.repo.index.diff(None)]
            untracked = self.repo.untracked_files
            if rel_path in untracked:
                return "new (git)"
            elif rel_path in changed:
                return "changed (git)"
        except Exception as e:
            logging.warning(f"Git status error: {e}")
        return None

    def calculate_file_hash(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logging.warning(f"Ошибка при вычислении хеша: {file_path} — {e}")
            return ""

    def analyze_imports(self, file_path):
        if not file_path.endswith('.py'):
            return set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=file_path)
        except Exception as e:
            logging.warning(f"Ошибка разбора AST: {file_path} — {e}")
            return set()

        imports = set()
        current_dir = os.path.dirname(file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                level = node.level or 0
                if level > 0:
                    base_path = current_dir
                    for _ in range(level - 1):
                        base_path = os.path.dirname(base_path)
                    module_path = os.path.join(base_path, module.replace('.', '/'))
                    module_path += '.py' if not os.path.isdir(module_path) else '/__init__.py'

                    if os.path.exists(module_path):
                        rel = os.path.relpath(module_path, self.project_root)
                        imports.add(rel[:-3].replace('/', '.'))
                else:
                    imports.add(module.split('.')[0])

        project_imports = set()
        for imp in imports:
            target = self.find_file_by_module(imp)
            if target:
                project_imports.add(target)
            elif any(f"{imp}/" in path for path in self.file_hashes):
                project_imports.add(f"{imp}/")

        return project_imports

    def analyze_templates(self, file_path):
        if not file_path.endswith('.py'):
            return set()

        templates = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            templates |= set(re.findall(r'render\([^)]*,\s*[\'"]([^\'"]+\.html)[\'"]', content))
            templates |= set(re.findall(r'template_name\s*=\s*[\'"]([^\'"]+\.html)[\'"]', content))
        except Exception as e:
            logging.warning(f"Ошибка анализа шаблонов: {file_path} — {e}")

        return {os.path.normpath(tpl) for tpl in templates}

    def scan_project(self):
        file_data = []
        self.import_graph.clear()
        self.template_graph.clear()

        for root, dirs, files in os.walk(self.project_root):
            if any(part in EXCLUDE_DIRS for part in root.split(os.sep)):
                continue

            for file in files:
                if file.endswith(('.py', '.html', '.md')):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.project_root)
                    status = self.get_file_status(full_path)

                    label = f"{file} ({status})" if status else file

                    print(f"Добавляем: {rel_path} — {label}")  # временно

                    file_data.append((rel_path, label))

                    if file.endswith('.py'):
                        imports = self.analyze_imports(full_path)
                        for imp in imports:
                            self.import_graph[rel_path].add(imp)

                        if 'views' in rel_path or 'urls' in rel_path:
                            templates = self.analyze_templates(full_path)
                            for tpl in templates:
                                tpl_path = self.find_template_file(tpl)
                                if tpl_path:
                                    self.template_graph[rel_path].add(tpl_path)

        return file_data

    def find_file_by_module(self, module_name):
        guesses = [
            f"{module_name.replace('.', '/')}.py",
            f"{module_name.replace('.', '/')}/__init__.py",
            f"{module_name}.py"
        ]
        for guess in guesses:
            if guess in self.file_hashes:
                return guess
            for path in self.file_hashes:
                if path.endswith(guess):
                    return path
        return None

    def find_template_file(self, template):
        for loc in [os.path.join(self.project_root, 'templates', template),
                    os.path.join(self.project_root, template)]:
            if os.path.exists(loc):
                return os.path.relpath(loc, self.project_root)
        return None

    def safe_id(self, path):
        return re.sub(r'[^a-zA-Z0-9_]', '_', path)

    def generate_file_structure_diagram(self, file_data):
        diagram = ["```mermaid", "graph TD"]
        for path, label in file_data:
            parent = os.path.dirname(path)
            if parent:
                diagram.append(f'{self.safe_id(parent)} --> {self.safe_id(path)}')
            diagram.append(f'{self.safe_id(path)}["{label}"]')
        diagram.append("```")
        return "\n".join(diagram)

    def generate_imports_diagram(self):
        diagram = ["```mermaid", "graph LR"]
        for src, targets in self.import_graph.items():
            for tgt in targets:
                diagram.append(f'{self.safe_id(src)} --> {self.safe_id(tgt)}')
        diagram.append("```")
        return "\n".join(diagram)

    def generate_templates_diagram(self):
        diagram = ["```mermaid", "graph LR"]
        for view, templates in self.template_graph.items():
            for template in templates:
                diagram.append(f'{self.safe_id(view)} --> {self.safe_id(template)}')
        diagram.append("```")
        return "\n".join(diagram)

    def generate_git_changes_diagram(self):
        if not self.repo:
            return "# Git changes\n\nGit repository not found"
        diagram = ["```mermaid", "gitGraph"]
        try:
            commits = list(self.repo.iter_commits('HEAD', max_count=10))
            commits.reverse()
            for commit in commits:
                diagram.append(f'    commit id:"{commit.hexsha[:7]}" tag:"{commit.summary}"')
        except Exception as e:
            return f"# Git changes\n\nError: {e}"
        diagram.append("```")
        return "\n".join(diagram)

    def generate_docs(self):
        file_data = self.scan_project()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        os.makedirs(self.output_dir, exist_ok=True)

        files = {
            "file_structure.md": self.generate_file_structure_diagram(file_data),
            "imports_dependencies.md": self.generate_imports_diagram(),
            "templates_usage.md": self.generate_templates_diagram(),
            "git_changes.md": self.generate_git_changes_diagram()
        }

        for filename, content in files.items():
            try:
                with open(os.path.join(self.output_dir, filename), 'w', encoding='utf-8') as f:
                    f.write(f"# {filename.replace('_', ' ').title()}\nGenerated at: {timestamp}\n\n")
                    f.write(content)
            except Exception as e:
                logging.error(f"Не удалось записать {filename}: {e}")

        self.save_hashes()
        logging.info(f"Документация сгенерирована в: {self.output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Django Project Visualizer")
    parser.add_argument("project_path", nargs="?", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        help="Путь к корню проекта Django")
    args = parser.parse_args()

    analyzer = AdvancedDjangoAnalyzer(args.project_path)
    analyzer.generate_docs()
