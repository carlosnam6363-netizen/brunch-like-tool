javascript:(function(){
    if (window.__brunchLikeBotActive) { alert('이미 실행 중입니다.'); return; }
    window.__brunchLikeBotActive = true;
    
    const panel = document.createElement('div');
    panel.id = 'brunch-like-bot-panel';
    panel.style.cssText = 'position:fixed;top:20px;right:20px;width:340px;background:#ffffff;border:2px solid #00c6be;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,0.25);z-index:999999;padding:16px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;color:#0f172a;font-size:13px;';
    
    panel.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;border-bottom:1px solid #e2e8f0;padding-bottom:8px;">
            <b style="font-size:15px;color:#00c6be;">💖 브런치 연재글 자동 좋아요</b>
            <button id="blb-close" style="border:none;background:none;font-size:18px;cursor:pointer;color:#94a3b8;">&times;</button>
        </div>
        <div style="margin-bottom:8px;">
            <label style="font-weight:600;">연재 요일: </label>
            <select id="blb-day" style="padding:4px 8px;border-radius:6px;border:1px solid #cbd5e1;font-size:12px;">
                <option value="TUESDAY" selected>화요일 (tue - 기본)</option>
                <option value="MONDAY">월요일 (mon)</option>
                <option value="WEDNESDAY">수요일 (wed)</option>
                <option value="THURSDAY">목요일 (thu)</option>
                <option value="FRIDAY">금요일 (fri)</option>
                <option value="SATURDAY">토요일 (sat)</option>
                <option value="SUNDAY">일요일 (sun)</option>
                <option value="COMPLETE">완결작 (com)</option>
            </select>
        </div>
        <div style="margin-bottom:10px;">
            <label style="font-weight:600;">랜덤 간격: </label>
            <input type="number" id="blb-min" value="1" min="1" max="60" style="width:42px;padding:3px;border-radius:4px;border:1px solid #cbd5e1;text-align:center;"> 초 ~
            <input type="number" id="blb-max" value="30" min="1" max="60" style="width:42px;padding:3px;border-radius:4px;border:1px solid #cbd5e1;text-align:center;"> 초
        </div>
        <button id="blb-start" style="width:100%;padding:10px;background:#00c6be;color:#fff;border:none;border-radius:8px;font-weight:bold;cursor:pointer;font-size:14px;box-shadow:0 4px 10px rgba(0,198,190,0.3);">🚀 1~30초 랜덤 좋아요 시작</button>
        <div id="blb-status" style="margin-top:10px;font-size:12px;color:#475569;max-height:120px;overflow-y:auto;background:#f8fafc;padding:8px;border-radius:6px;border:1px solid #e2e8f0;white-space:pre-wrap;">준비 완료. [시작] 버튼을 누르세요.</div>
    `;
    document.body.appendChild(panel);
    
    let isRunning = false;
    let stopRequested = false;
    const logBox = panel.querySelector('#blb-status');
    const startBtn = panel.querySelector('#blb-start');
    
    function log(msg) {
        const time = new Date().toTimeString().split(' ')[0];
        logBox.innerText = `[${time}] ${msg}\n` + logBox.innerText.slice(0, 600);
    }
    
    panel.querySelector('#blb-close').onclick = () => {
        stopRequested = true;
        panel.remove();
        window.__brunchLikeBotActive = false;
    };
    
    startBtn.onclick = async () => {
        if (isRunning) {
            stopRequested = true;
            startBtn.innerText = '중단 요청됨...';
            return;
        }
        isRunning = true;
        stopRequested = false;
        startBtn.style.background = '#ef4444';
        startBtn.innerText = '⏹️ 좋아요 작업 중단';
        
        const day = panel.querySelector('#blb-day').value;
        const minSec = Math.max(1, parseInt(panel.querySelector('#blb-min').value) || 1);
        const maxSec = Math.max(minSec, parseInt(panel.querySelector('#blb-max').value) || 30);
        
        log(`'${day}' 연재 글 목록 수집 중...`);
        try {
            const listUrl = `https://api.brunch.co.kr/v2/serial-brunchbook/all?dayOfWeek=${day}&orderKeyword=PUBLISH_TIME&serialStatus=${day==='COMPLETE'?'COMPLETE':'ONGOING'}`;
            const listResp = await fetch(listUrl, { credentials: 'include' });
            const listJson = await listResp.json();
            const items = (listJson.data && listJson.data.list) || [];
            
            if (items.length === 0) {
                log('수집된 글이 없습니다.');
                resetBtn();
                return;
            }
            
            log(`총 ${items.length}개의 글 발견! ${minSec}~${maxSec}초 랜덤 시작.`);
            let success = 0, skipped = 0, failed = 0;
            
            for (let i = 0; i < items.length; i++) {
                if (stopRequested) { log('작업이 중단되었습니다.'); break; }
                const art = items[i];
                const pageUrl = `https://brunch.co.kr/@@${art.userId}/${art.articleNo}`;
                log(`[${i+1}/${items.length}] '${art.articleTitle}' 확인 중...`);
                
                try {
                    const pageResp = await fetch(pageUrl, { credentials: 'include' });
                    const html = await pageResp.text();
                    
                    if (html.includes('"isLiked":true')) {
                        skipped++;
                        log(`ℹ️ [스킵] 이미 좋아요됨`);
                    } else {
                        const tokenMatch = html.match(/name=["']secure-token["']\s+content=["']([^"']+)["']/);
                        const token = tokenMatch ? tokenMatch[1] : '';
                        const likeUrl = `https://api.brunch.co.kr/v1/likeit?articleUserId=${encodeURIComponent(art.userId)}&articleNo=${art.articleNo}`;
                        const likeResp = await fetch(likeUrl, {
                            method: 'POST',
                            headers: { 'X-CSRF-TOKEN': token, 'Accept': 'application/json' },
                            credentials: 'include'
                        });
                        if (likeResp.status === 200) {
                            success++;
                            log(`💖 [성공] 좋아요 완료!`);
                        } else {
                            failed++;
                            log(`⚠️ [실패] HTTP ${likeResp.status}`);
                        }
                    }
                } catch(e) {
                    failed++;
                    log(`❌ [오류] ${e.message}`);
                }
                
                if (i < items.length - 1 && !stopRequested) {
                    const wait = Math.floor(Math.random() * (maxSec - minSec + 1)) + minSec;
                    for (let r = wait; r > 0; r--) {
                        if (stopRequested) break;
                        startBtn.innerText = `⏳ 다음 글까지 ${r}초 대기 중... (중단: 클릭)`;
                        await new Promise(res => setTimeout(res, 1000));
                    }
                    startBtn.innerText = '⏹️ 좋아요 작업 중단';
                }
            }
            log(`🎉 완료! 성공:${success}건, 스킵:${skipped}건, 실패:${failed}건`);
        } catch(e) {
            log(`오류 발생: ${e.message}`);
        }
        resetBtn();
    };
    
    function resetBtn() {
        isRunning = false;
        startBtn.style.background = '#00c6be';
        startBtn.innerText = '🚀 1~30초 랜덤 좋아요 시작';
    }
})();
