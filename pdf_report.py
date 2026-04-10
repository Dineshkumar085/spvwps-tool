# from weasyprint import HTML
# from io import BytesIO
# from datetime import datetime
 
 
# def generate_pdf_report(data: dict) -> BytesIO:
#     html_str = _build_html(data)
#     buf = BytesIO()
#     HTML(string=html_str).write_pdf(buf)
#     buf.seek(0)
#     return buf
 
 
# def _inr(v):
#     try:
#         return f"\u20b9{int(v):,}"
#     except Exception:
#         return str(v) if v else "—"
 
 
# def _build_html(d: dict) -> str:
#     gen_date = datetime.now().strftime("%d %B %Y, %I:%M %p")
#     lat = d.get('lat', '—')
#     lon = d.get('lon', '—')
 
#     crop_rows = ""
#     for r in d.get('results', []):
#         crop_rows += f"""<tr>
#           <td>{r.get('crop','')}</td><td>{r.get('area_ha','')}</td>
#           <td>{r.get('days','')}</td><td>{r.get('kc_avg','')}</td>
#           <td>{r.get('etc_day','')}</td><td>{r.get('rain_mm','')}</td>
#           <td>{r.get('pe_mm','')}</td><td>{r.get('cwr_m3','')}</td>
#           <td>{r.get('nir_m3','')}</td>
#           <td>{int(r.get('app_eff',0)*100)}%</td>
#           <td><b>{r.get('gir_m3','')}</b></td></tr>"""
 
#     P_des = d.get('P_design_kW','—')
#     dh    = d.get('daily_hours','—')
#     psh   = d.get('PSH','—')
#     pr    = d.get('system_PR','—')
#     try:
#         e_d = round(float(P_des) * float(dh), 2)
#     except Exception:
#         e_d = '—'
 
#     cost_rows = ""
#     for label, key in [
#         ("PV Modules (&#8377;25,000/kWp)",           "cost_pv_module_cost"),
#         ("Pump + Motor (&#8377;5,000/HP)",            "cost_pump_motor_cost"),
#         ("Inverter/Controller (&#8377;10,000/kWp)",   "cost_inverter_cost"),
#         ("Mounting Structure (&#8377;6,000/kWp)",     "cost_mounting_cost"),
#         ("BOS + Civil Works (&#8377;4,000/kWp)",      "cost_civil_bos_cost"),
#         ("Miscellaneous/Contingency",                 "cost_misc_cost"),
#     ]:
#         cost_rows += f"<tr><td>{label}</td><td class='r'>{_inr(d.get(key,''))}</td></tr>"
#     cost_rows += f"<tr class='tot'><td><b>TOTAL PROJECT COST</b></td><td class='r'><b>{_inr(d.get('cost_total_cost',''))}</b></td></tr>"
 
#     sub_rows = f"""
#     <tr><td>Central Govt CFA</td><td class='r'>{_inr(d.get('cost_subsidy_central',''))}</td><td class='r g'>30%</td></tr>
#     <tr><td>State Govt Subsidy</td><td class='r'>{_inr(d.get('cost_subsidy_state',''))}</td><td class='r g'>30%</td></tr>
#     <tr><td>Bank Loan</td><td class='r'>{_inr(d.get('cost_loan',''))}</td><td class='r'>30%</td></tr>
#     <tr class='tot'><td><b>Farmer Share</b></td><td class='r'><b>{_inr(d.get('cost_farmer_share',''))}</b></td><td class='r'><b>10%</b></td></tr>
#     <tr><td>Annual Diesel Saving</td><td class='r'>{_inr(d.get('cost_annual_saving_est',''))}/yr</td><td>—</td></tr>
#     <tr><td>Payback Period</td><td class='r' colspan='2'>~{d.get('cost_payback_years','—')} years</td></tr>"""
 
#     ann = d.get('annual_energy_gen','—')
#     try:
#         ann = f"{int(ann):,}"
#     except Exception:
#         pass
 
#     pe_pct = d.get('pump_eta_pct','—')
#     me_pct = d.get('motor_eta_pct','—')
#     try:
#         pe_f = pe_pct/100
#     except Exception:
#         pe_f = '?'
#     try:
#         me_f = me_pct/100
#     except Exception:
#         me_f = '?'
 
#     qlps = d.get('Q_lps','—')
#     try:
#         q_m3s = round(float(qlps)/1000, 6)
#     except Exception:
#         q_m3s = '?'
 
#     return f"""<!DOCTYPE html>
# <html><head><meta charset="UTF-8"/>
# <style>
# @page {{ size:A4; margin:16mm 14mm 16mm 14mm;
#   @bottom-center {{ content:"Page " counter(page) " of " counter(pages);
#     font-size:7pt; color:#999; }} }}
# *{{box-sizing:border-box;margin:0;padding:0;}}
# body{{font-family:Arial,sans-serif;font-size:9pt;color:#2c3e50;line-height:1.5;}}
# .tb{{background:#1a5276;color:#fff;padding:12px 16px 8px;border-radius:5px;margin-bottom:7px;}}
# .tb h1{{font-size:14pt;margin-bottom:2px;}}
# .tb p{{font-size:8pt;opacity:.8;}}
# .mr{{display:flex;border:0.5px solid #d5d8dc;border-radius:4px;overflow:hidden;margin-bottom:8px;}}
# .mc{{flex:1;padding:5px 9px;font-size:7.5pt;background:#f4f6f9;border-right:0.5px solid #d5d8dc;}}
# .mc:last-child{{border-right:none;}}
# .sh{{background:#1a5276;color:#fff;padding:4px 9px;font-size:9pt;font-weight:bold;
#   border-radius:4px;margin:10px 0 5px;}}
# .kb{{display:flex;border:0.5px solid #bee3f8;border-radius:4px;overflow:hidden;margin-bottom:5px;}}
# .kp{{flex:1;padding:6px 8px;background:#eaf4fb;border-right:0.5px solid #bee3f8;text-align:center;}}
# .kp:last-child{{border-right:none;}}
# .kp .v{{font-size:12pt;font-weight:bold;color:#1a5276;}}
# .kp .u{{font-size:6.5pt;color:#7f8c8d;}}
# .kp .l{{font-size:7pt;margin-top:1px;}}
# .kp.hi{{background:#d4efdf;}}
# .kp.hi .v{{color:#1a7a4a;}}
# table{{width:100%;border-collapse:collapse;font-size:7.5pt;margin-bottom:5px;}}
# th{{background:#1a5276;color:#fff;padding:4px 5px;text-align:center;}}
# td{{padding:3.5px 5px;border-bottom:0.3px solid #d5d8dc;text-align:center;}}
# tr:nth-child(even) td{{background:#f4f6f9;}}
# .tot td{{background:#eaf4fb;font-weight:bold;color:#1a5276;border-top:1px solid #1a5276;}}
# td:first-child{{text-align:left;}}
# .r{{text-align:right;}}
# .g{{color:#1a7a4a;font-weight:bold;}}
# .fb{{background:#f0f4f8;border-left:3px solid #1a5276;padding:6px 9px;
#   font-family:'Courier New',monospace;font-size:7pt;color:#1a5276;
#   line-height:1.9;margin-bottom:7px;border-radius:0 4px 4px 0;}}
# .disc{{background:#fef9e7;border:0.8px solid #f39c12;border-left:3px solid #f39c12;
#   padding:7px 10px;font-size:7.5pt;color:#7d6608;border-radius:0 4px 4px 0;margin:9px 0 5px;}}
# .ft{{border-top:0.5px solid #d5d8dc;padding-top:5px;text-align:center;
#   font-size:7.5pt;color:#7f8c8d;line-height:1.9;margin-top:6px;}}
# .ref{{font-size:7.5pt;padding:2px 0 2px 16px;position:relative;
#   border-bottom:0.3px dashed #d5d8dc;}}
# .ref .n{{position:absolute;left:0;font-weight:bold;color:#1a5276;}}
# .pb{{page-break-before:always;}}
# .two{{display:flex;gap:10px;}}
# .two>div{{flex:1;}}
# </style></head><body>
 
# <div class="tb">
#   <h1>Solar PV Water Pumping System (SPVWPS) &mdash; Design Report</h1>
#   <p>FAO-56 Penman-Monteith &nbsp;|&nbsp; PM-KUSUM Cost Structure &nbsp;|&nbsp; NASA POWER Climate Data</p>
# </div>
# <div class="mr">
#   <div class="mc"><b>Generated:</b> {gen_date}</div>
#   <div class="mc"><b>Location:</b> {lat}&deg;N, {lon}&deg;E</div>
#   <div class="mc"><b>Prepared by:</b> Dinesh Kumar, RPCAU Pusa</div>
# </div>
 
# <div class="sh">1. &nbsp; Climate Summary &nbsp;(NASA POWER API &mdash; 22-year Climatology)</div>
# <div class="kb">
#   <div class="kp"><div class="v">{d.get('temp_avg','&mdash;')}</div><div class="u">&deg;C</div><div class="l">Mean Temp</div></div>
#   <div class="kp"><div class="v">{d.get('rh_avg','&mdash;')}</div><div class="u">%</div><div class="l">Rel. Humidity</div></div>
#   <div class="kp"><div class="v">{d.get('rad_avg','&mdash;')}</div><div class="u">MJ/m&sup2;/day</div><div class="l">Solar Radiation</div></div>
#   <div class="kp"><div class="v">{d.get('PSH','&mdash;')}</div><div class="u">h/day</div><div class="l">Peak Sun Hours</div></div>
#   <div class="kp"><div class="v">{d.get('eto_avg','&mdash;')}</div><div class="u">mm/day</div><div class="l">Annual ET&#8320;</div></div>
#   <div class="kp"><div class="v">{d.get('daily_hours','&mdash;')}</div><div class="u">h/day</div><div class="l">Pump Hours</div></div>
# </div>
 
# <div class="sh">2. &nbsp; Crop Water Requirement &nbsp;(FAO-56 Single Kc Method)</div>
# <table>
#   <thead><tr><th>Crop</th><th>Area(ha)</th><th>Days</th><th>Kc</th>
#   <th>ETc(mm/d)</th><th>Rain(mm)</th><th>Eff.Rain</th>
#   <th>CWR(m&sup3;)</th><th>NIR(m&sup3;)</th><th>App.Eff</th><th>GIR(m&sup3;)</th></tr></thead>
#   <tbody>{crop_rows}
#   <tr class="tot"><td colspan="7"><b>TOTAL</b></td>
#   <td><b>{d.get('total_cwr_m3','&mdash;')}</b></td><td></td><td></td>
#   <td><b>{d.get('total_net_m3','&mdash;')}</b></td></tr></tbody>
# </table>
# <div class="fb">ET&#8320; = FAO-56 PM Eq.6 = [0.408*&#916;*Rn + &#947;*(900/(T+273))*u2*(es-ea)] / [&#916; + &#947;*(1+0.34*u2)]
# ETc  = Kc * ET&#8320;  |  CWR = ETc * Days * Area * 10 [m&sup3;]  |  Pe = Rain * 0.70 (USDA-SCS TR-21)
# NIR  = max(CWR - Pe, 0)  &rarr;  GIR = NIR / Field Application Efficiency</div>
 
# <div class="sh">3. &nbsp; Hydraulic Design &amp; Pump Sizing</div>
# <div class="kb">
#   <div class="kp"><div class="v">{d.get('Q_lps','&mdash;')}</div><div class="u">L/s</div><div class="l">Flow Rate Q</div></div>
#   <div class="kp"><div class="v">{d.get('Q_m3h','&mdash;')}</div><div class="u">m&sup3;/h</div><div class="l">Flow Rate Q</div></div>
#   <div class="kp"><div class="v">{d.get('P_hyd_kW','&mdash;')}</div><div class="u">kW</div><div class="l">Hydraulic Pwr</div></div>
#   <div class="kp"><div class="v">{d.get('P_shaft_kW','&mdash;')}</div><div class="u">kW</div><div class="l">Shaft Power</div></div>
#   <div class="kp"><div class="v">{d.get('P_motor_kW','&mdash;')}</div><div class="u">kW</div><div class="l">Motor Input</div></div>
#   <div class="kp"><div class="v">{d.get('P_design_kW','&mdash;')}</div><div class="u">kW</div><div class="l">Design(+20%)</div></div>
#   <div class="kp hi"><div class="v">{d.get('pump_hp','&mdash;')} HP</div><div class="u">std</div><div class="l">Selected Pump</div></div>
# </div>
# <div class="fb">Q = GIR / (Season_days x Hrs x 3600) = {d.get('total_net_m3','?')} / ({d.get('max_season_days','?')} x {dh} x 3600) = {qlps} L/s
# P_hyd = &rho;*g*Q*H = 1000*9.81*{q_m3s}*{d.get('TDH','?')} = {d.get('P_hyd_kW','?')} kW
# P_shaft = P_hyd / &eta;p = {d.get('P_hyd_kW','?')} / {pe_f} = {d.get('P_shaft_kW','?')} kW
# P_motor = P_shaft / &eta;m = {d.get('P_shaft_kW','?')} / {me_f} = {d.get('P_motor_kW','?')} kW
# P_design = P_motor * 1.20 (ISO 9906) = {d.get('P_design_kW','?')} kW &rarr; {d.get('pump_hp','?')} HP (standard)</div>
 
# <div class="sh">4. &nbsp; Solar PV Array Sizing</div>
# <div class="kb">
#   <div class="kp"><div class="v">{d.get('solar_kWp','&mdash;')}</div><div class="u">kWp</div><div class="l">PV Array</div></div>
#   <div class="kp"><div class="v">{d.get('panels_required','&mdash;')}</div><div class="u">x400Wp</div><div class="l">Panels</div></div>
#   <div class="kp"><div class="v">{d.get('overall_efficiency','&mdash;')}%</div><div class="u">overall</div><div class="l">System Eff.</div></div>
#   <div class="kp"><div class="v">{ann}</div><div class="u">kWh/yr</div><div class="l">Est. Gen.</div></div>
# </div>
# <div class="fb">E_daily = P_design * Hours = {P_des} * {dh} = {e_d} kWh/day
# PV_kWp = E_daily / (PSH * PR) = {e_d} / ({psh} * {pr}) = {d.get('solar_kWp','?')} kWp
# Panels = {d.get('solar_kWp','?')} / 0.40 = {d.get('panels_required','?')} panels (400 Wp each)  [Cuadros et al., 2004]</div>
 
# <div class="pb"></div>
# <div class="sh">5. &nbsp; Techno-Economic Analysis &nbsp;(PM-KUSUM Scheme, India 2025-26)</div>
# <div class="two">
#   <div>
#     <table><thead><tr><th style="text-align:left">Cost Component</th><th>Amount</th></tr></thead>
#     <tbody>{cost_rows}</tbody></table>
#   </div>
#   <div>
#     <table><thead><tr><th style="text-align:left">PM-KUSUM Financing</th><th>Amount</th><th>Share</th></tr></thead>
#     <tbody>{sub_rows}</tbody></table>
#   </div>
# </div>
 
# <div class="sh">6. &nbsp; References</div>
# <div class="ref"><span class="n">[1]</span> Allen, R.G. et al. (1998). FAO Irrigation &amp; Drainage Paper No. 56. FAO, Rome.</div>
# <div class="ref"><span class="n">[2]</span> Habib, S. et al. (2023). Technical modelling of SPVWPS. <em>Heliyon</em>, 9(5), e16105.</div>
# <div class="ref"><span class="n">[3]</span> Hilarydoss, S. (2023). Sizing, economics of solar PV water pumping. <em>Environ Sci Pollut Res</em>, 30, 71491.</div>
# <div class="ref"><span class="n">[4]</span> Cuadros, F. et al. (2004). Solar-powered irrigation sizing. <em>Solar Energy</em>, 76(4), 465&ndash;473.</div>
# <div class="ref"><span class="n">[5]</span> MNRE (2024). PM-KUSUM Scheme Comprehensive Guidelines. Govt. of India.</div>
# <div class="ref"><span class="n">[6]</span> USDA-SCS (1967). Irrigation Water Requirements. Technical Release No. 21.</div>
# <div class="ref"><span class="n">[7]</span> NASA POWER Project. Prediction of Worldwide Energy Resource API v2. power.larc.nasa.gov</div>
 
# <div class="disc"><b>Disclaimer:</b> This report is for academic/research purposes (B.Tech Final Year Project, RPCAU Pusa).
# Results are based on NASA POWER climatological averages and FAO-56 standard coefficients.
# Validate with certified solar system designers before field implementation.</div>
 
# <div class="ft">
#   <b>Developed by Dinesh Kumar</b> &nbsp;|&nbsp; B.Tech Agricultural Engineering, RPCAU Pusa, Bihar<br/>
#   Guide: <b>Dr. Ravish Chandra</b> &mdash; Dept. of Agricultural Engineering, RPCAU Pusa<br/>
#   Dr. Rajendra Prasad Central Agricultural University, Pusa, Samastipur, Bihar &mdash; 848125
# </div>
 
# </body></html>"""
