// Point-by-point Markov model (Barnett-Clarke style). Pure functions, no DOM.
function gameWin(p){const q=1-p;return p**4*(1+4*q+10*q*q)+20*p**3*q**3*p*p/(p*p+q*q);}
function tbWin(sA,rA,aFirst){
  const pt=(sA+rA)/2,q=1-pt,tie=pt*pt/(pt*pt+q*q),memo={};
  function f(a,b,k){
    if((a>=7||b>=7)&&Math.abs(a-b)>=2)return a>b?1:0;
    if(a>=6&&b>=6){const d=a-b;return d===0?tie:d===1?pt+q*tie:pt*tie;}
    const key=a+','+b;if(memo[key]!==undefined)return memo[key];
    const aServes=(((k+1)>>1)%2===0)===aFirst,p=aServes?sA:rA;
    return memo[key]=p*f(a+1,b,k+1)+(1-p)*f(a,b+1,k+1);
  }
  return f(0,0,0);
}
function setWin(hA,hB,sA,rA,aFirst){
  const memo={};
  function f(a,b,aServes){
    if((a>=6||b>=6)&&Math.abs(a-b)>=2)return a>b?1:0;
    if(a===6&&b===6)return tbWin(sA,rA,aServes);
    const key=a+','+b;if(memo[key]!==undefined)return memo[key];
    const pg=aServes?hA:1-hB;
    return memo[key]=pg*f(a+1,b,!aServes)+(1-pg)*f(a,b+1,!aServes);
  }
  return f(0,0,aFirst);
}
// spwA/rpwA: A's serve/return points won (0-1); same for B. bestOf 3 or 5.
function matchWin(spwA,rpwA,spwB,rpwB,bestOf){
  const ft=(spwA+spwB+(1-rpwA)+(1-rpwB))/4;           // tour average approximated from the two players
  const sA=spwA-rpwB+(1-ft), sB=spwB-rpwA+(1-ft);     // A's / B's point-win prob on own serve
  const rA=1-sB, hA=gameWin(sA), hB=gameWin(sB);
  const s=(setWin(hA,hB,sA,rA,true)+setWin(hA,hB,sA,rA,false))/2;
  const m=bestOf===5?s**3*(10-15*s+6*s*s):s*s*(3-2*s);
  return {p:m,set:s,sA,sB,hA,hB};
}
if(typeof module!=='undefined')module.exports={gameWin,tbWin,setWin,matchWin};
