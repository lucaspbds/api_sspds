import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any

class CrimeService:
    @staticmethod
    def listar_ocorrencias(limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Serviço responsável por buscar ocorrências criminais na pasta database.
        Lê o arquivo JSON gerado pelo serviço de ingestão.
        """
        database_dir = Path(os.getenv("DATABASE_PATH", "database"))
        file_path = database_dir / "dados.json"
        
        # Se o arquivo ainda não existir, retorna uma lista vazia com segurança
        if not file_path.exists():
            return []
        
        # Lê o conteúdo do JSON gerado pela ingestão
        with open(file_path, "r", encoding="utf-8") as f:
            dados = json.load(f)    
        # Se um limite foi especificado, fatia a lista; senão, retorna tudo
        if limit is not None:
            return dados[:limit]
        return dados