import concurrent.futures,json,uuid
TIERS={'extract':'economy','classify':'economy','score':'local','write':'balanced','review':'balanced','strategy':'premium'}
PROVIDER_MODELS={'codex':{'economy':'luna','balanced':'terra','premium':'sol'},'claude':{'economy':'haiku','balanced':'sonnet','premium':'opus'},'heuristic':{'local':'rules','economy':'rules','balanced':'rules','premium':'rules'}}
def estimate_tokens(text):return max(1,len(text)//4)
def route(task_type,provider='heuristic',force_tier=None):
 tier=force_tier or TIERS.get(task_type,'economy');return {'provider':provider,'tier':tier,'model':PROVIDER_MODELS.get(provider,PROVIDER_MODELS['heuristic']).get(tier,'rules')}
def execute_parallel(tasks,worker,max_workers=4):
 run_id=uuid.uuid4().hex
 with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:results=list(pool.map(lambda t:worker(run_id,t),tasks))
 return {'run_id':run_id,'results':results}
