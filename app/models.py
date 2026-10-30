from pydantic import BaseModel,Field
class ProfileIn(BaseModel):
 full_name:str='';email:str='';phone:str='';city:str='';course:str='Bacharelado em Tecnologia da Informação';term:int=Field(2,ge=1,le=20);graduation_date:str='';linkedin:str='';github:str='';target_roles:list[str]=[];skills:list[str]=[];evidence:list[dict]=[];preferences:dict={}
class JobIn(BaseModel):
 title:str;company:str;url:str='';location:str='';work_model:str='';description:str;salary_min:float|None=None;benefits:list[str]=[];source:str='manual';external_id:str=''
class StageIn(BaseModel):stage:str
class SourceIn(BaseModel):name:str;kind:str=Field(pattern='^(rss|api)$');url:str;config:dict={}
class ProviderIn(BaseModel):provider:str=Field(pattern='^(heuristic|codex|claude)$')
