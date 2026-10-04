"""Run with: python -m streamlit run app.py"""
import json,os
import streamlit as st
from aai.config import ROOT,load_config,load_env
from aai.storage import Store
from aai.controllers import Controller

st.set_page_config(page_title='Adaptive Inference | Phase 1',page_icon='🔀',layout='wide')
load_env();cfg=load_config();store=Store(ROOT/'outputs/runs.sqlite')
@st.cache_resource
def engine(config_hash):
    from aai.pipeline import Engine
    return Engine(load_config(),Store(ROOT/'outputs/runs.sqlite'))

st.title('Agentic Adaptive Inference Framework')
st.caption('Phase 1 · Local query analysis · Free API inference · Explicit routing decisions')
with st.sidebar:
    st.header('Inference strategy')
    labels={'Formula-Based':'formula','Online Adaptive':'online','Hybrid':'hybrid','Always-Strongest Baseline':'baseline'}
    label=st.selectbox('Routing mode',list(labels));mode=labels[label]
    namespace=st.text_input('Controller workspace','default',help='Use separate names for separate experiments. Training and testing must use the same name.')
    learn=st.checkbox('Enable learning from feedback',value=False,disabled=mode not in ('online','hybrid'))
    st.caption('Keep learning off for held-out tests. Human feedback updates only the starting arm using the whole inference trajectory.')
    st.divider();st.subheader('Model configuration')
    for i,m in enumerate(cfg['models'],1):st.write(f'**Tier {i}:** {m["id"]}')
    st.caption('Capability ordering is provisional until pilot evaluation. Free access must be confirmed in each provider account.')
    st.write('Configuration:',cfg['version'])
    st.warning('Weights and thresholds are provisional; calibration is still required.')

ready=all(os.getenv(k) for k in ('GEMINI_API_KEY','GROQ_API_KEY')) and os.getenv('FREE_TIER_CONFIRMED','').lower()=='true'
if not ready:
    st.info('Setup: copy .env.example to .env, enter both API keys locally, and confirm that both provider projects remain on free plans. Restart Streamlit after editing .env. Keys are never displayed here.')
query_tab,history_tab=st.tabs(['Ask a query','Run history'])
with query_tab:
    with st.form('query_form'):
        query=st.text_area('Your query',height=120,placeholder='Explain supervised and unsupervised learning with examples.',max_chars=cfg['max_input_chars'])
        submit=st.form_submit_button('Run inference',disabled=not ready)
    if submit:
        try:
            with st.spinner('Analyzing and generating. Free-tier throttling may add up to a minute per call…'):
                st.session_state['last_run']=engine(cfg['hash']).run(query,mode,learn,namespace)
        except Exception as exc:
            st.error(f'Could not complete the run ({type(exc).__name__}). Check the terminal. For setup problems, run python -m aai.cli doctor.')
            # Streamlit logs the exception locally; provider errors already have sanitized messages.
            if isinstance(exc,ValueError):st.write(str(exc))
    run=st.session_state.get('last_run')
    if run:
        st.subheader('Response')
        if run['status']=='needs_review':st.warning('The strongest attempted tier did not meet the adequacy threshold. Showing the best measured attempt; review it.')
        elif run['status'] not in ('completed',):st.warning(run.get('error') or run['final_evaluation'].get('reason') or run['status'])
        elif run['final_evaluation']['status']=='unchecked':st.info('Basic checks passed. Semantic correctness was not independently verified.')
        st.markdown(run['response'] or 'No answer was generated.')
        st.subheader('Inference report')
        a=run['analysis'];m=run['metrics'];cols=st.columns(4)
        cols[0].metric('Complexity',f'{a["complexity"]:.3f}',a['complexity_level'])
        cols[1].metric('Active latency',f'{m["active_latency_seconds"]:.2f} s')
        cols[2].metric('Reported tokens',m['total_tokens'])
        score=run['final_evaluation'].get('score');cols[3].metric('Adequacy proxy','Unmeasured' if score is None else f'{score:.2f}')
        st.write(f'**Mode:** {run["mode"]} · **Task:** {a["semantic"]["task"]} · **Status:** {run["status"]}')
        st.write(f'**Initial model:** {run["decision"]["initial_model"]}')
        st.write(f'**Retrieval:** {run["retrieval"]["status"]} · **Verification calls:** {m["verification_calls"]} · **Escalations:** {m["escalations"]}')
        st.caption(f'Quota wait: {m["quota_wait_seconds"]:.2f}s. API calls: {m["api_calls"]}. ₹0 on your confirmed free plans. Tokens are a resource proxy, not measured FLOPs.')
        if not m['token_usage_complete']:st.caption('Token totals may be incomplete; no missing usage is invented.')
        with st.expander('Why this route?'):
            st.write(run['decision']['reasons']);st.json(a['features']);st.json(a['semantic'])
        with st.expander('Evidence and attempt evaluations'):
            st.json(run['retrieval']);st.json(run['attempts'])
        if run.get('reward'):st.write('Applied reward:',run['reward'])
        elif run.get('learning_enabled') and run['status'] in ('completed','needs_review'):
            st.write('Provide quality feedback to update this controller. Scores must reflect the answer, not which model produced it.')
            with st.form('feedback_'+run['id']):
                rel=st.slider('Relevance',0.,1.,.5,.05);comp=st.slider('Completeness',0.,1.,.5,.05);correct=st.slider('Correctness / task quality',0.,1.,.5,.05)
                apply=st.form_submit_button('Save feedback and update controller')
            if apply:
                try:
                    Controller(cfg,store).feedback(run,(rel+comp+correct)/3,'human_ui')
                    st.session_state['last_run']=store.get(run['id']);st.rerun()
                except ValueError as exc:st.error(str(exc))
        st.download_button('Download this inference report',json.dumps(run,indent=2,ensure_ascii=False),file_name=run['id']+'.json',mime='application/json')
with history_tab:
    runs=store.recent(100)
    st.caption('Latest 100 runs. Benchmark commands export the complete experiment.')
    if runs:
        st.dataframe([{'Run':r['id'][:12],'Mode':r['mode'],'Query':r['analysis']['original'],'Status':r['status'],
                       'Initial tier':r['decision']['initial_tier']+1,'Tokens':r.get('metrics',{}).get('total_tokens'),
                       'Reward':r.get('reward',{}).get('value') if r.get('reward') else None} for r in runs],hide_index=True)
        selected=st.selectbox('Inspect a run',[r['id'] for r in runs])
        with st.expander('Full stored report'):st.json(store.get(selected))
    else:st.write('No runs recorded yet.')
