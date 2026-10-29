"""Author: Ethan. Browser acceptance against an already launched downloaded app."""
import argparse
import json
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

parser=argparse.ArgumentParser();parser.add_argument('--base-url',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
    browser=pw.chromium.launch()
    page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
    page.goto(args.base_url)
    page.get_by_role('button',name='Use synthetic sample').click()
    expect(page.get_by_role('heading',level=2,name='synthetic-sample.txt')).to_be_visible(timeout=15000)
    page.get_by_role('button',name='Run local review').click()
    expect(page.get_by_text('Review complete.',exact=True)).to_be_visible(timeout=20000)
    page.locator('.issue-card').first.click()
    quote=page.locator('.finding-detail .source-card > p').first.inner_text()
    page.get_by_role('button',name='View in source').first.click()
    expect(page.locator('.source-highlight p')).to_have_text(quote)
    page.get_by_role('tab',name='Findings').click()
    page.get_by_role('button',name='Confirm finding').click()
    expect(page.locator('.issue-card').first.locator('.issue-status')).to_have_text('Confirmed')
    with page.expect_download() as download:page.get_by_label('Export review').select_option('json')
    target=args.output/'review.json';download.value.save_as(target)
    report=json.loads(target.read_text());assert any(i['status']=='accepted' for i in report['issues'])
    page.reload()
    expect(page.locator('.issue-card').first.locator('.issue-status')).to_have_text('Confirmed')
    # Exercise the revision workflow in the installed app, not a source server.
    with urllib.request.urlopen(args.base_url + '/api/documents/' + report['document_id']) as response:
        original = json.load(response)
    revision_text = original['text'] + '\nThe foregoing cap does not apply to confidentiality obligations.'
    page.get_by_label('Choose a revised contract').set_input_files({'name':'synthetic-revision.txt','mimeType':'text/plain','buffer':revision_text.encode()})
    expect(page.get_by_role('heading',name='synthetic-revision.txt',exact=True)).to_be_visible(timeout=15000)
    page.get_by_role('button',name='Run review',exact=True).click()
    expect(page.get_by_role('heading',name='Compare saved reviews')).to_be_visible(timeout=20000)
    expect(page.get_by_text('Revisit prior decisions',exact=False).first).to_be_visible()
    with page.expect_download() as revision_download:
        page.get_by_role('link',name='Export comparison JSON').click()
    comparison_path=args.output/'comparison.json';revision_download.value.save_as(comparison_path)
    comparison=json.loads(comparison_path.read_text())
    assert comparison['before_review_id']==report['id']
    assert comparison['text_changes'] and any(r['revisit_prior_decisions'] for r in comparison['rules'])
    assert all(i['status']=='unresolved' and not i['notes'] for r in comparison['rules'] for i in r['after_issues'])
    with urllib.request.urlopen(args.base_url + '/api/reviews/' + report['id']) as response:
        earlier=json.load(response)
    assert any(i['status']=='accepted' for i in earlier['issues'])
    page.screenshot(path=str(args.output/'review.png'),full_page=True)
    browser.close()
(args.output/'result.json').write_text(json.dumps({'author':'Ethan','status':'PASS','checks':['installed app browser first task','source passage navigation','finding decision','actual export','returning saved review','installed revision upload, comparison export, fresh decisions and preserved baseline'],'limits':['Automated developer test, not an unfamiliar-user study']},indent=2)+'\n')
print('PASS: installed app first-task and returning browser journey')
