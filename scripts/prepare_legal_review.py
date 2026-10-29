"""Build blind, source-based review materials without running the app. Author: Ethan."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
CATEGORIES=['Governing Law','Cap On Liability','Anti-Assignment','Termination For Convenience']

def prepare(archive,output):
    contract=json.loads((ROOT/'evaluation/release-contract.json').read_text())
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==contract['held_out']['archive_sha256']
    output.mkdir(parents=True,exist_ok=False)
    (output/'blind').mkdir();(output/'reference').mkdir()
    with ZipFile(archive) as z:
        all_data=json.loads(z.read('CUADv1.json'))['data']
        exposed=json.loads(z.read('test.json'))['data']
    development=next(e for e in exposed if e['title'].startswith('CENTRACKINTERNATIONALINC_'))
    selected=[('development-01',development)]+[(f'held-out-{i+1:02}',next(e for e in all_data if e['title']==title)) for i,title in enumerate(contract['held_out']['titles'])]
    manifests=[]
    for id,entry in selected:
        assert len(entry['paragraphs'])==1
        paragraph=entry['paragraphs'][0];text=paragraph['context'];raw=text.encode()
        (output/'blind'/f'{id}.txt').write_bytes(raw)
        spans=[]
        for q in paragraph['qas']:
            category=q['id'].rsplit('__',1)[-1]
            if category not in CATEGORIES:continue
            for a in q['answers']:
                start=a['answer_start'];end=start+len(a['text']);assert text[start:end]==a['text']
                spans.append({'category':category,'start':start,'end':end,'quote':a['text']})
        reference={'author':'Ethan','source_author':'The Atticus Project; Hendrycks, Burns, Chen and Ball','title':entry['title'],'license':'CC BY 4.0','source':'https://github.com/The-Atticus-Project/cuad','source_sha256':hashlib.sha256(raw).hexdigest(),'judgment_scope':'Independent upstream provision-identification labels only; not risk, enforceability or exception-effect judgments','spans':spans}
        (output/'reference'/f'{id}.json').write_text(json.dumps(reference,indent=2)+'\n')
        worksheet={'author':'Ethan','case_id':id,'reviewer':None,'qualifications':None,'date':None,'client_side':None,'transaction_context':None,'complete_original_and_exhibits_verified':None,'extraction_fidelity':None,'issue_detection':None,'legal_interpretation':None,'source_references':[],'material_misses':[],'unsupported_assertions':[],'unresolved_questions':[],'blind_judgment_locked_before_app_output':False,'adjudicator':None,'adjudication':None}
        (output/'blind'/f'{id}-worksheet.json').write_text(json.dumps(worksheet,indent=2)+'\n')
        manifests.append({'case_id':id,'title':entry['title'],'sha256':reference['source_sha256'],'source_kind':'complete upstream CUAD context; original-file/exhibit completeness must be checked by reviewer','app_evaluated':False,'reserved_from_project_tuning':id.startswith('held-out')})
    # Complete public cover-and-standard-terms examples; existing project inputs,
    # therefore development material, never relabeled as held-out.
    provenance=json.loads((ROOT/'corpus/public/provenance.json').read_text())
    for item in provenance['sources']:
        p=ROOT/'corpus/public'/item['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
        shutil.copy2(p,output/'blind'/p.name)
        manifests.append({**item,'case_id':p.stem,'source_kind':'complete public template, cover and standard terms; unfilled business terms require context','reserved_from_project_tuning':False})
    notes={'author':'Ethan','status':'PROVISIONAL implementer-authored source-reading notes; independent legal acceptance pending','case':'development-01','judgments':[{'category':'Cap On Liability','reference':'Upstream exact quote and offsets in reference/development-01.json','reading':'An express monetary limit refers to one month of fees plus the remaining prepaid portion. This does not establish the configured preceding-12-month aggregate-fee position. Review scope, remedies and all exceptions.','expected_screen':'located, unresolved; not absent and not approved'},{'category':'Termination For Convenience','reference':'Upstream exact quote and offsets in reference/development-01.json; read following payment sentence in full source','reading':'Either party may terminate without cause on thirty days written notice. The following sentence preserves amounts due; it does not by itself establish acceleration of all future fees. Client materiality and enforceability require independent review.','expected_screen':'locate the right; inspect the payment qualification separately'}],'public_template_tasks':['Review both cover and standard terms; do not invent unfilled business terms.','Identify confidentiality exclusions, permitted recipients and survival; distinguish these from agreement duration.','For a clean revision, lock a source-based judgment about changed scope before viewing comparison output.']}
    (output/'reference/provisional-development-notes.json').write_text(json.dumps(notes,indent=2)+'\n')
    shutil.copy2(ROOT/'evaluation/release-contract.json',output/'rubric.json')
    (output/'manifest.json').write_text(json.dumps({'author':'Ethan','cases':manifests,'held_out_use':'Reserved for a future qualified reviewer; no app evaluation or tuning on these four cases in this release','original_archive_sha256':contract['held_out']['archive_sha256']},indent=2)+'\n')
    (output/'READ-FIRST.txt').write_text('Author: Ethan\nIndependent legal acceptance: PENDING.\n\nGive reviewers blind/ and rubric.json first. Reference/ contains external identification labels and explicitly provisional development notes; keep it hidden until reviewers lock their own judgments. Verify complete originals/exhibits and specify client context. Record exact source spans, definitions, exceptions, separate limits, precedence and revision effects. Do not mark unknown as pass. Preserve all failures and disagreements; adjudicate consequential differences with a second qualified reviewer. Only then run a frozen app and compare outputs. Report extraction, detection and interpretation separately with per-case denominators. No aggregate legal-accuracy score. Four held-out cases have not been used for fixes or app evaluation. They are held out from this project, not claimed unseen in model training. Public templates are development material.\n\nCUAD attribution: The Atticus Project; Dan Hendrycks, Collin Burns, Anya Chen, Spencer Ball (2021), CC BY 4.0, https://github.com/The-Atticus-Project/cuad. Common Paper templates retain their original notices; CC BY 4.0, https://commonpaper.com/standards/. No confidential documents or paid reviewer engagement.\n')
    return manifests

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    cases=prepare(a.archive,a.output);print(json.dumps({'cases':len(cases),'held_out':sum(x.get('reserved_from_project_tuning',False) for x in cases)}))
