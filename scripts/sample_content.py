"""Content for the two demo handbooks.

All content is fictional and belongs to the invented company "Northwind Freight
Group". Verticals are deliberately restricted to logistics/freight operations
and corporate HR — see README invariant 1 (non-compete isolation).

Structure: a document is a list of (heading, [paragraph, ...]) blocks. A heading
of "" means the paragraphs continue the previous block. Numbered headings are
what the loader's section detector picks up, so keep the "N.N Title" shape.
"""

from __future__ import annotations

LOGISTICS_HANDBOOK = {
    "filename": "Global_Logistics_Operating_Handbook.pdf",
    "title": "Global Logistics Operating Handbook & Policy Manual",
    "subtitle": "Northwind Freight Group — Operations Standard, Revision 4.1",
    "footer": "Northwind Freight Group — Internal Operations Document — Revision 4.1",
    "blocks": [
        ("1 Purpose and Scope", [
            "This handbook defines the mandatory operating standard for all Northwind Freight Group terminals, "
            "dispatch centres, and contracted carrier partners. It applies to every shipment moving under a "
            "Northwind booking reference, regardless of mode, origin, or customer contract tier.",
            "Where a customer's master service agreement imposes a stricter requirement than this handbook, the "
            "customer agreement prevails and the terminal manager must record the deviation in the shipment file. "
            "Where a customer agreement is silent, this handbook is the controlling document.",
        ]),
        ("1.1 Document Control", [
            "This handbook is revised twice yearly. The Operations Standards Committee owns the content; the "
            "Quality Assurance function owns distribution. Superseded revisions must be withdrawn from terminal "
            "noticeboards within ten working days of a new release.",
            "Local work instructions may expand on this handbook but may never relax a control defined in it. "
            "Any proposed relaxation requires written approval from the Director of Operations.",
        ]),
        ("1.2 Definitions", [
            "\"On-duty dispatcher\" means the named individual holding the dispatch roster slot at the time an "
            "event occurs, including weekend and public holiday slots. \"Terminal\" means any Northwind-operated "
            "or Northwind-leased facility where freight is received, held, or transferred. \"Contracted carrier\" "
            "means a third-party haulier operating under a Northwind carrier agreement.",
            "\"Cold-chain cargo\" means any consignment booked with a contracted temperature set point, including "
            "chilled, frozen, and controlled ambient goods. \"Set point\" is the target temperature stated on the "
            "booking; \"deviation\" is any measured departure from that set point.",
        ]),
        ("2 Roles and Responsibilities", [
            "Accountability for a shipment transfers with physical custody, but escalation duties do not. The "
            "originating dispatch centre retains escalation ownership for the full transit, even after the freight "
            "has left its region.",
        ]),
        ("2.1 On-Duty Dispatcher", [
            "The on-duty dispatcher monitors active shipments, acknowledges telematics and sensor alarms, and "
            "initiates the escalation paths in Section 4 and Section 7. The dispatcher may not close an alarm "
            "without either resolving it or handing it to a named owner.",
            "Dispatchers work a continuous roster. Handover at shift change requires a written handover note "
            "listing every open alarm, its age, and its assigned owner. An open alarm may never be handed over "
            "verbally.",
        ]),
        ("2.2 Terminal Operations Supervisor", [
            "The terminal operations supervisor controls physical movement of freight within the facility, "
            "including hold decisions. When a consignment is placed on hold under Section 4, the supervisor is "
            "responsible for physically segregating it and applying a hold tag bearing the shipment reference and "
            "the time of the hold.",
        ]),
        ("2.3 Cold-Chain Quality Lead", [
            "The cold-chain quality lead is the sole authority permitted to release temperature-deviated cargo for "
            "onward movement or to authorise disposal. There is a named primary and a named deputy for every "
            "region, and one of the two is on call at all times including weekends.",
            "The quality lead reviews all Form CC-12 submissions within one working day and records a disposition "
            "decision against each one.",
        ]),
        ("3 Freight Handling", [
            "All freight must be received against a booking reference. Freight arriving without a booking "
            "reference is quarantined in the unidentified freight bay and reported to the originating dispatch "
            "centre the same day.",
        ]),
        ("3.1 Booking and Pre-Advice", [
            "Bookings close four hours before the scheduled terminal cut-off for domestic movements and twelve "
            "hours before cut-off for cross-border movements. Late bookings may be accepted only by the terminal "
            "operations supervisor and only where capacity is confirmed.",
            "Cold-chain bookings must state the set point, the permitted tolerance band, and the sensor "
            "configuration. A cold-chain booking submitted without a stated set point is rejected automatically "
            "and returned to the customer for correction.",
        ]),
        ("3.2 Documentation", [
            "Every consignment travels with a transport document, a packing list, and — where applicable — the "
            "customs declaration set. Documentation is checked at loading, not at booking, because contents "
            "frequently change between the two events.",
            "Missing documentation is a loading stopper for cross-border freight and a recorded exception for "
            "domestic freight. Domestic freight may proceed with a recorded exception; cross-border freight may "
            "not proceed under any circumstance.",
        ]),
        ("3.3 Loading and Securing", [
            "Load securing follows the regional load-restraint code applicable at the point of loading. Where "
            "origin and destination codes differ, the stricter of the two applies for the whole journey.",
            "Mixed loads combining cold-chain and ambient freight in one compartment are prohibited unless the "
            "compartment is physically partitioned and separately sensored.",
        ]),
        ("4 Cold-Chain and Perishable Cargo", [
            "Cold-chain freight is the highest-risk category Northwind handles, both commercially and in terms of "
            "product safety. The controls in this section are mandatory and may not be relaxed by local work "
            "instruction.",
        ]),
        ("4.1 Pre-Cooling and Loading", [
            "Trailers and containers carrying cold-chain freight must be pre-cooled to the contracted set point "
            "and must hold that temperature for thirty minutes before loading begins. Pre-cooling is evidenced by "
            "the unit's own log, which is attached to the shipment file.",
            "Loading a cold-chain consignment into a unit that has not achieved and held the set point is a "
            "reportable control failure, and the loading is stopped until a compliant unit is available.",
        ]),
        ("4.2 Temperature Deviation and Weekend Escalation", [
            "A temperature deviation is any measured departure of more than 2°C from the contracted set point "
            "sustained for more than fifteen minutes. Deviations of 4°C or more are treated as temperature "
            "abuse and trigger the escalation below regardless of duration.",
            "In the event of a weekend or public holiday temperature deviation exceeding 4°C above the "
            "contracted set point, the on-duty dispatcher must notify the cold-chain quality lead within two hours "
            "of the alarm being raised and must initiate Form CC-12 before the goods leave the terminal. The "
            "consignment is placed on hold and physically segregated pending the quality lead's disposition "
            "decision. Under no circumstance may temperature-abused perishable cargo continue to the consignee on "
            "a dispatcher's own authority.",
            "Where the deviation is detected in transit rather than at a terminal, the vehicle is routed to the "
            "nearest Northwind facility or approved partner facility with cold storage, and the two-hour "
            "notification clock runs from the alarm, not from arrival.",
            "Weekend escalation uses the on-call quality lead rota published in Appendix B. If the primary "
            "on-call lead cannot be reached within thirty minutes, the dispatcher escalates to the deputy, and "
            "then to the Director of Operations. An unanswered escalation is never a reason to release cargo.",
        ]),
        ("4.3 Form CC-12 Cold-Chain Incident Record", [
            "Form CC-12 is the controlled record for every temperature deviation. It captures the shipment "
            "reference, the set point, the measured peak deviation, the duration, the sensor identifier, the time "
            "the alarm was raised, the time the quality lead was notified, and the physical location of the goods "
            "at the time of the hold.",
            "The form must be initiated by the dispatcher who acknowledged the alarm and completed within four "
            "hours. An incomplete CC-12 blocks invoicing of the affected consignment.",
        ]),
        ("4.4 Disposition of Deviated Cargo", [
            "The cold-chain quality lead selects one of four dispositions: release to consignee, release with "
            "customer notification and concession, return to shipper, or controlled disposal. Disposal requires a "
            "witnessed disposal certificate signed by two Northwind employees.",
            "Cargo released with a concession must be accompanied by the CC-12 summary so the consignee can make "
            "their own acceptance decision. Concealing a deviation from a consignee is a disciplinary matter.",
        ]),
        ("5 Carrier Performance, Claims and Credits", [
            "Carrier performance is measured monthly and reviewed quarterly with each contracted carrier. "
            "Persistent underperformance triggers the remediation ladder in Section 5.1.",
        ]),
        ("5.1 On-Time In-Full Measurement", [
            "On-time in-full (OTIF) is measured against the promised delivery window, not the carrier's own "
            "estimate. A delivery is on time if it arrives within the promised window; it is in full if the "
            "delivered quantity matches the transport document without shortage or damage.",
            "A carrier falling below 94 per cent OTIF in two consecutive months enters a documented improvement "
            "plan. A carrier falling below 88 per cent in any single month is suspended from new bookings until "
            "the improvement plan is agreed.",
        ]),
        ("5.2 Damage and Loss Claims", [
            "Claims for visible damage must be noted on the delivery receipt at the point of delivery. Claims for "
            "concealed damage must be raised within seven calendar days of delivery for domestic movements and "
            "within fourteen calendar days for international movements.",
            "Northwind acknowledges a claim within three working days and issues a determination within twenty "
            "working days of receiving complete supporting evidence. Incomplete claims are held, and the "
            "determination clock does not start until the file is complete.",
        ]),
        ("5.3 Refunds and Service Credits", [
            "Where Northwind has failed a contracted service level, the customer is entitled to a service credit "
            "against the freight charge for the affected consignment. Service credits are applied to the next "
            "invoice rather than refunded to source, unless the customer account is closing.",
            "The refund window for international customers is thirty calendar days from the invoice date, "
            "extended to sixty calendar days where a customs authority hold caused the delay. Domestic customers "
            "have a fourteen-calendar-day refund window. Requests received outside the window are handled as "
            "goodwill claims and require commercial approval.",
        ]),
        ("6 Hazardous and Restricted Goods", [
            "Northwind accepts limited classes of dangerous goods only at nominated terminals with trained staff "
            "and current facility approvals. Acceptance is by exception, never by default.",
        ]),
        ("6.1 Acceptance Screening", [
            "Every booking is screened against the restricted commodity list at submission. Flagged bookings are "
            "routed to the dangerous goods safety adviser, who either approves the movement with conditions or "
            "rejects it.",
            "Undeclared dangerous goods discovered in a consignment are isolated immediately, the shipper is "
            "notified, and the incident is reported to the safety adviser the same day.",
        ]),
        ("6.2 Segregation in Storage", [
            "Segregation distances follow the applicable modal dangerous goods code. Where a terminal cannot "
            "achieve the required segregation, the consignment is refused rather than stored non-compliantly.",
        ]),
        ("7 Customer Communication Standards", [
            "Customers are told about problems by Northwind, not by their consignee. Proactive notification is "
            "the standard, and the timings below are contractual minimums.",
        ]),
        ("7.1 Notification Timings", [
            "A delay expected to exceed four hours is notified to the customer within one hour of it becoming "
            "known. A cold-chain deviation is notified within four hours of the alarm, in parallel with the "
            "internal escalation in Section 4.2. A loss is notified immediately upon confirmation.",
            "First response to an inbound customer enquiry is within four working hours. Substantive resolution "
            "or a dated plan is provided within two working days.",
        ]),
        ("7.2 Escalation Matrix", [
            "Tier one is the account coordinator. Tier two is the regional operations manager, reached when an "
            "issue is unresolved after two working days or where the value at risk exceeds twenty-five thousand "
            "euro. Tier three is the Director of Operations, reached for any product safety issue, any regulatory "
            "notification, or any issue affecting more than five customers simultaneously.",
        ]),
        ("Appendix A — Controlled Forms Register", [
            "CC-12 Cold-Chain Incident Record. CL-04 Damage and Loss Claim. DG-02 Dangerous Goods Acceptance "
            "Condition Sheet. HO-07 Shipment Hold Tag. HV-01 Shift Handover Note. DS-03 Witnessed Disposal "
            "Certificate.",
            "Controlled forms are issued only from the document management system. Locally recreated versions of "
            "a controlled form are invalid and must not be used in a shipment file.",
        ]),
        ("Appendix B — On-Call Escalation Rota", [
            "The cold-chain on-call rota names a primary and deputy quality lead per region for every calendar "
            "week, including public holidays. The rota is published two weeks in advance and republished within "
            "one hour of any change.",
            "Dispatchers must use the current published rota rather than stored personal contact details. Using a "
            "superseded contact does not satisfy the notification requirement in Section 4.2.",
        ]),
    ],
}

EMPLOYEE_HANDBOOK = {
    "filename": "Employee_Handbook_2026.pdf",
    "title": "Employee Handbook 2026",
    "subtitle": "Northwind Freight Group — People Policy Manual",
    "footer": "Northwind Freight Group — Employee Handbook 2026 — Confidential",
    "blocks": [
        ("1 About This Handbook", [
            "This handbook describes the terms, benefits, and expectations that apply to all Northwind Freight "
            "Group employees. It is not a contract of employment; your individual contract and any collective "
            "agreement take precedence where they differ.",
            "Where this handbook is silent, ask your manager or the People team rather than assuming. Local "
            "statutory entitlements always apply in addition to what is written here.",
        ]),
        ("2 Employment Basics", [
            "Northwind hires into defined roles with published grade bands. Role changes are made through the "
            "internal move process rather than informal reassignment.",
        ]),
        ("2.1 Probation Period", [
            "New employees serve a six-month probation period, reduced to three months for internal transfers. "
            "During probation either party may end the employment with two weeks' notice. Probation is confirmed "
            "in writing; it does not lapse into confirmation automatically.",
        ]),
        ("2.2 Working Hours and Shift Patterns", [
            "The standard working week is forty hours. Terminal and dispatch roles operate rotating shifts "
            "published four weeks in advance. A published shift may be changed with less than seven days' notice "
            "only by agreement with the employee.",
            "Employees working a night shift, defined as any shift with more than three hours falling between "
            "23:00 and 06:00, receive the night shift allowance described in Section 3.3.",
        ]),
        ("2.3 Remote and Hybrid Work", [
            "Office-based roles may work remotely up to three days per week with manager agreement. Terminal, "
            "dispatch, and driver roles are on-site by nature and are not eligible for hybrid work.",
            "Remote work outside your country of employment requires prior People team approval and is limited to "
            "twenty working days per calendar year, because of tax and social security consequences.",
        ]),
        ("3 Compensation and Payroll", [
            "Salaries are reviewed annually with effect from 1 April. Reviews consider role band, performance, "
            "and market position.",
        ]),
        ("3.1 Pay Cycle", [
            "Salaries are paid monthly on the 25th, or the last working day before the 25th where that date falls "
            "on a weekend or public holiday. Payslips are available in the employee portal two working days "
            "before payment.",
            "Payroll corrections are made in the next available cycle. An underpayment of more than ten per cent "
            "of net pay is corrected by off-cycle payment within five working days of being confirmed.",
        ]),
        ("3.2 Overtime", [
            "Overtime is worked only when authorised in advance by a manager. Authorised overtime is paid at 1.5 "
            "times base hourly rate on weekdays and Saturdays, and at 2.0 times base hourly rate on Sundays and "
            "public holidays.",
            "Employees in grade band 6 and above are not eligible for overtime payment and instead take time off "
            "in lieu, agreed with their manager and taken within three months.",
        ]),
        ("3.3 Shift and On-Call Allowances", [
            "The night shift allowance is twenty per cent of base hourly rate for qualifying hours. On-call duty "
            "outside working hours attracts a flat weekly on-call allowance, plus overtime for any hours actually "
            "worked while on call.",
            "On-call rotas are published two weeks in advance. An employee may not be rostered on call for more "
            "than one week in four without their agreement.",
        ]),
        ("4 Benefits", [
            "Benefits begin on the first day of employment unless stated otherwise. Coverage levels are reviewed "
            "annually and confirmed in the benefits summary issued each January.",
        ]),
        ("4.1 Medical Cover", [
            "All employees are enrolled in the company medical plan from their start date. The plan covers "
            "primary consultations, specialist referrals, and hospital treatment within the plan network. "
            "Out-of-network treatment is reimbursed at seventy per cent of the in-network rate.",
            "Dependants may be added within thirty days of your start date, or within thirty days of a qualifying "
            "life event such as marriage or the birth of a child. Outside those windows, additions wait for the "
            "annual enrolment window in November.",
        ]),
        ("4.2 Dental Cover", [
            "Dental cover is included in the company medical plan at no additional employee contribution. "
            "Preventive treatment, defined as two check-ups and one hygienist visit per calendar year, is covered "
            "in full with no co-pay.",
            "Restorative treatment carries a twenty per cent co-pay, capped at one hundred and fifty euro per "
            "treatment episode and at six hundred euro per employee per calendar year. Orthodontic treatment "
            "carries a fifty per cent co-pay with a lifetime cap of two thousand euro, and is available to "
            "employees and enrolled dependants after twelve months of continuous plan membership.",
            "Cosmetic dentistry is excluded from the plan entirely. Pre-authorisation is required for any single "
            "course of treatment expected to exceed eight hundred euro.",
        ]),
        ("4.3 Vision Cover", [
            "The plan reimburses one eye examination per calendar year in full, and contributes up to two hundred "
            "euro every two years towards prescription glasses or lenses. Employees who use display screens for "
            "more than four hours a day may claim a screen-use examination annually, separate from the standard "
            "entitlement.",
        ]),
        ("4.4 Pension", [
            "Northwind contributes six per cent of base salary to the company pension from the start date, rising "
            "to eight per cent after five years of service. Employee contributions are voluntary and are matched "
            "up to a further two per cent.",
            "Contribution changes take effect from the following pay cycle and may be made twice per calendar "
            "year without restriction.",
        ]),
        ("5 Leave and Absence", [
            "Leave is tracked in the employee portal. Verbal approval is not a record; leave must be entered and "
            "approved in the system before it is taken.",
        ]),
        ("5.1 Annual Leave", [
            "Full-time employees receive twenty-five days of annual leave per calendar year, accrued monthly. "
            "Employees with more than five years of service receive twenty-eight days.",
            "Up to five unused days may be carried into the following year and must be taken by 31 March. Days "
            "beyond five are forfeited unless carry-over was blocked by an operational refusal, in which case the "
            "full balance carries.",
        ]),
        ("5.2 Sickness Absence", [
            "Report sickness absence to your manager before your shift start, or within one hour of it where that "
            "is not possible. Self-certification covers the first seven calendar days; absence beyond seven days "
            "requires a medical certificate.",
            "Company sick pay is full pay for the first twenty working days of absence in any rolling twelve-month "
            "period, then statutory pay thereafter. A return-to-work conversation is held after any absence of "
            "more than five working days.",
        ]),
        ("5.3 Parental Leave", [
            "Parental leave follows the statutory entitlement of your country of employment, topped up by "
            "Northwind to full pay for the first sixteen weeks. The top-up applies to both parents and is not "
            "reduced if both parents work for Northwind.",
            "Notice of intended parental leave is required at least eight weeks before the planned start. Return "
            "to the same role is guaranteed for absences of up to twelve months.",
        ]),
        ("5.4 Unpaid and Special Leave", [
            "Unpaid leave of up to three months may be granted at the manager's discretion after two years of "
            "service. Bereavement leave is five paid days for an immediate family member and two paid days "
            "otherwise. Two paid days per year are available for civic duties such as jury service where these "
            "are not separately compensated.",
        ]),
        ("6 Travel and Expenses", [
            "Business travel is booked through the corporate travel tool. Bookings made outside the tool are "
            "reimbursed only where the tool was unavailable and the exception is documented.",
        ]),
        ("6.1 Booking and Class of Travel", [
            "Flights under six hours are booked in economy class. Flights over six hours may be booked in premium "
            "economy with director approval. Rail travel is booked in standard class, or first class where the "
            "fare is lower than the standard flexible fare for the same journey.",
            "Hotels are booked within the published city caps. Where no room is available inside the cap, book "
            "the nearest available option and note the reason in the expense claim.",
        ]),
        ("6.2 Per Diem and Meals", [
            "A per diem covers meals and incidental costs and is paid at the published country rate. Where a meal "
            "is provided by the company or a host, the per diem is reduced by the corresponding meal fraction: "
            "twenty per cent for breakfast, thirty per cent for lunch, and fifty per cent for dinner.",
            "Alcohol is not reimbursable except at a client-facing event approved in advance by a director.",
        ]),
        ("6.3 Claim Deadlines", [
            "Expense claims must be submitted within thirty days of the expense being incurred, with receipts "
            "attached for any item above twenty-five euro. Claims submitted after sixty days are paid only with "
            "finance director approval.",
            "Approved claims are reimbursed in the next payroll cycle. Reimbursement is never made in cash.",
        ]),
        ("7 Conduct and Acceptable Use", [
            "Northwind expects honest, safe, and respectful behaviour from everyone, at every site, and in every "
            "interaction with customers and carrier partners.",
        ]),
        ("7.1 Standards of Conduct", [
            "Harassment, discrimination, and retaliation are prohibited and are treated as gross misconduct. "
            "Concerns may be raised with any manager, the People team, or the confidential reporting line, and may "
            "be raised anonymously.",
            "Safety-critical roles are subject to a zero-tolerance standard on alcohol and drugs during working "
            "hours and while on call.",
        ]),
        ("7.2 Information and IT Acceptable Use", [
            "Company systems are provided for business use. Limited personal use is acceptable where it does not "
            "interfere with work or breach any other policy. Customer data may not be copied to personal devices "
            "or personal cloud accounts under any circumstances.",
            "Report a suspected security incident, including a lost device or a suspicious message, to the IT "
            "service desk immediately. Reporting promptly is never itself a disciplinary matter.",
        ]),
        ("Appendix — Who to Contact", [
            "People team for pay, benefits, and leave questions. Payroll for payslip and tax code corrections. IT "
            "service desk for access and security incidents. Confidential reporting line for conduct concerns. "
            "Contact details are published on the intranet contacts page and reviewed monthly.",
        ]),
    ],
}

DOCUMENTS = [LOGISTICS_HANDBOOK, EMPLOYEE_HANDBOOK]
