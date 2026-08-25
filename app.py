import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB='jamil_tarabar.db'

def db(): return sqlite3.connect(DB)

def init():
    c=db()
    c.execute('''CREATE TABLE IF NOT EXISTS barnameh(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      barnameh_no TEXT UNIQUE NOT NULL, date TEXT, sender TEXT, receiver TEXT,
      driver TEXT, vehicle_type TEXT, plate TEXT, national_id TEXT, shaba TEXT,
      freight REAL DEFAULT 0, commission_pct REAL DEFAULT 0, commission REAL DEFAULT 0,
      driver_payable REAL DEFAULT 0, status TEXT DEFAULT 'ثبت اولیه')''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, barnameh_no TEXT, driver TEXT,
      amount REAL, payment_date TEXT, method TEXT, note TEXT)''')
    c.commit(); c.close()
init()

st.set_page_config(page_title='جمیل ترابر',layout='wide')
st.title('سامانه مدیریت جمیل ترابر')
st.caption('نسخه اولیه MVP')
menu=st.sidebar.radio('منو',['داشبورد','ثبت بارنامه','بارنامه‌ها','ورود Excel','پرداخت راننده'])

if menu=='داشبورد':
    c=db(); b=pd.read_sql('SELECT * FROM barnameh',c); p=pd.read_sql('SELECT * FROM payments',c); c.close()
    cols=st.columns(4)
    vals=[('تعداد بارنامه',len(b)),('جمع کرایه',b.freight.sum() if len(b) else 0),('جمع کمیسیون',b.commission.sum() if len(b) else 0),('پرداخت رانندگان',p.amount.sum() if len(p) else 0)]
    for col,(n,v) in zip(cols,vals): col.metric(n,f'{v:,.0f}')
    st.dataframe(b.sort_values('id',ascending=False).head(20),use_container_width=True)

elif menu=='ثبت بارنامه':
    with st.form('bar'):
        a,b,c=st.columns(3)
        no=a.text_input('شماره بارنامه *'); date=b.date_input('تاریخ',datetime.now()); sender=c.text_input('فرستنده')
        receiver=a.text_input('گیرنده'); driver=b.text_input('راننده'); vehicle=c.text_input('نوع خودرو')
        plate=a.text_input('پلاک'); nid=b.text_input('کد ملی راننده'); shaba=c.text_input('شبا')
        freight=a.number_input('کرایه',min_value=0.0,step=100000.0); pct=b.number_input('درصد کمیسیون',min_value=0.0,max_value=100.0,step=0.1)
        save=st.form_submit_button('ثبت بارنامه')
    if save:
        try:
            com=freight*pct/100
            c=db(); c.execute('''INSERT INTO barnameh(barnameh_no,date,sender,receiver,driver,vehicle_type,plate,national_id,shaba,freight,commission_pct,commission,driver_payable) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(no,str(date),sender,receiver,driver,vehicle,plate,nid,shaba,freight,pct,com,freight-com)); c.commit(); c.close(); st.success('بارنامه ثبت شد.')
        except sqlite3.IntegrityError: st.error('این شماره بارنامه قبلاً ثبت شده است.')

elif menu=='بارنامه‌ها':
    q=st.text_input('جستجو: شماره بارنامه، راننده، کد ملی یا پلاک')
    c=db(); df=pd.read_sql('SELECT * FROM barnameh ORDER BY id DESC',c); c.close()
    if q:
        df=df[df.astype(str).apply(lambda s:s.str.contains(q,case=False,na=False)).any(axis=1)]
    st.dataframe(df,use_container_width=True)
    st.download_button('خروجی CSV',df.to_csv(index=False).encode('utf-8-sig'),'barnameh.csv','text/csv')

elif menu=='ورود Excel':
    f=st.file_uploader('فایل Excel راهداری',type=['xlsx','xls'])
    if f:
        raw=pd.read_excel(f); st.dataframe(raw.head(20),use_container_width=True)
        if st.button('وارد کردن اطلاعات'):
            aliases={'barnameh_no':['شماره بارنامه','بارنامه','barnameh_no'],'date':['تاریخ','date'],'sender':['فرستنده','مبدا','sender'],'receiver':['گیرنده','مقصد','receiver'],'driver':['راننده','نام راننده','driver'],'vehicle_type':['نوع خودرو','خودرو','vehicle_type'],'plate':['پلاک','plate'],'national_id':['کد ملی','کدملی','national_id'],'shaba':['شبا','شماره شبا','shaba'],'freight':['کرایه','مبلغ کرایه','freight'],'commission_pct':['درصد کمیسیون','کمیسیون','commission_pct']}
            cols={str(x).strip():x for x in raw.columns}; out={}
            for k,names in aliases.items():
                src=next((cols[n] for n in names if n in cols),None); out[k]=raw[src] if src else ['']*len(raw)
            x=pd.DataFrame(out); x['freight']=pd.to_numeric(x.freight,errors='coerce').fillna(0); x['commission_pct']=pd.to_numeric(x.commission_pct,errors='coerce').fillna(0); x['commission']=x.freight*x.commission_pct/100; x['driver_payable']=x.freight-x.commission
            c=db(); ok=dup=0
            for _,r in x.iterrows():
                try:
                    c.execute('''INSERT INTO barnameh(barnameh_no,date,sender,receiver,driver,vehicle_type,plate,national_id,shaba,freight,commission_pct,commission,driver_payable) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',tuple(r[k] for k in ['barnameh_no','date','sender','receiver','driver','vehicle_type','plate','national_id','shaba','freight','commission_pct','commission','driver_payable'])); ok+=1
                except sqlite3.IntegrityError: dup+=1
            c.commit(); c.close(); st.success(f'{ok} بارنامه وارد شد؛ {dup} مورد تکراری وارد نشد.')

else:
    c=db(); df=pd.read_sql('''SELECT b.barnameh_no,b.driver,b.driver_payable,COALESCE(SUM(p.amount),0) paid FROM barnameh b LEFT JOIN payments p ON b.barnameh_no=p.barnameh_no GROUP BY b.barnameh_no,b.driver,b.driver_payable ORDER BY b.id DESC''',c); c.close(); df['remaining']=df.driver_payable-df.paid; st.dataframe(df,use_container_width=True)
    with st.form('pay'):
        no=st.text_input('شماره بارنامه'); amount=st.number_input('مبلغ پرداخت',min_value=0.0,step=100000.0); method=st.selectbox('روش پرداخت',['کارت','بانک','نقدی','حواله','سایر']); note=st.text_input('توضیحات'); submit=st.form_submit_button('ثبت پرداخت')
    if submit:
        c=db(); row=c.execute('SELECT driver,driver_payable FROM barnameh WHERE barnameh_no=?',(no,)).fetchone()
        if not row: st.error('بارنامه پیدا نشد.')
        else:
            paid=c.execute('SELECT COALESCE(SUM(amount),0) FROM payments WHERE barnameh_no=?',(no,)).fetchone()[0]
            if paid+amount>row[1]: st.error(f'پرداخت بیشتر از مبلغ مجاز است. مانده: {row[1]-paid:,.0f}')
            elif amount<=0: st.error('مبلغ نامعتبر است.')
            else:
                c.execute('INSERT INTO payments(barnameh_no,driver,amount,payment_date,method,note) VALUES(?,?,?,?,?,?)',(no,row[0],amount,str(datetime.now()),method,note)); c.commit(); st.success('پرداخت ثبت شد.')
        c.close()
