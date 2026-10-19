// Original SVG cat family. Decorative images never replace accessible button names.
function catArt(kind='heart',className=''){return `<img class="cat-art ${className}" src="assets/cat-${kind}.svg" alt="" aria-hidden="true">`}
function miaoCoin(){return '<img class="miao-coin" src="assets/miao-coin.svg" alt="" aria-hidden="true">'}
function catButton(action,label,kind='wave'){return `<button class="cat-button" ${action} aria-label="${label}" title="${label}">${catArt(kind)}</button>`}
function walletDialog(){modal('我的喵币',`<div class="wallet-hero">${miaoCoin()}<h2>${communityState?.balance??0} <small>喵币</small></h2><p>每一份善意，都值得被记住。</p></div><p>「喵币」是平台互助积分的新名字。</p><p class="helper">邀请同学与参与公益的奖励仍为试点方案，待真实认证与完成核验接通后发放。当前不支持充值、提现或支付；订单奖励以喵币展示，尚未接入结算。</p><button class="btn primary" data-wallet-community>去看看校园公益</button>`)}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.hasAttribute('data-wallet'))walletDialog();if(b.hasAttribute('data-wallet-community')){$('#dialog').close();navigate('community')}});
