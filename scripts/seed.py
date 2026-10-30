import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
import json
from app.db import init_db,connect
from app.models import ProfileIn
init_db();p=ProfileIn(full_name='Kauan Inacio dos Santos',city='Presidente Venceslau, SP',term=2,target_roles=['Estágio em Desenvolvimento','Estágio em Automação','Estágio em TI','QA','Dados/BI'],skills=['python','playwright','git','github','sql','power bi','excel','api'],evidence=[{'name':'RelatPy sanitizado','description':'automação web em Python com processamento de arquivos, logs e dashboard'}],preferences={'salary_min':2000,'benefits':['vale alimentação'],'work_models':['remoto','híbrido','Presidente Prudente']})
with connect() as c:c.execute('INSERT OR REPLACE INTO profile(id,data) VALUES(1,?)',(p.model_dump_json(),))
print('Perfil inicial criado. Complete e-mail, telefone e links no painel.')
