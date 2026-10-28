"""Fixed vocabulary of claim documents.

Rule files, the Builder output and every answer key use these codes, which is what
makes checklist precision/recall computable (free-text checklist items could not be scored).
"""

DOC_CODES: dict[str, str] = {
    "DOC_DEATH_CERT": "Death certificate of the deceased (certified copy)",
    "DOC_LEGAL_HEIR_CERT": "Legal heir certificate issued by the competent authority",
    "DOC_SUCCESSION_CERT": "Succession certificate issued by a court",
    "DOC_INDEMNITY_BOND": "Indemnity bond by the claimant(s)",
    "DOC_NAME_VARIATION_AFFIDAVIT": "Affidavit explaining the name difference between records",
    "DOC_CLAIMANT_KYC": "KYC of the claimant (ID and address proof)",
    "DOC_NOMINEE_KYC": "KYC of the nominee",
    "DOC_CLAIM_FORM_BANK": "Bank's deceased-depositor claim form",
    "DOC_CLAIM_FORM_INSURER": "Insurer's death-claim form",
    "DOC_CLAIM_FORM_REGISTRY": "Share registry's claim form",
    "DOC_TRANSMISSION_FORM": "Transmission-of-shares request form",
    "DOC_POLICY_BOND": "Original life insurance policy bond / policy document",
    "DOC_FD_RECEIPT": "Fixed deposit receipt or passbook",
    "DOC_SHARE_CERT": "Share certificate or folio statement",
    "DOC_NOC_OTHER_HEIRS": "No-objection statements from other legal heirs",
    "DOC_DOB_PROOF": "Proof of date of birth of the deceased",
    "DOC_ADDRESS_CHANGE_PROOF": "Proof linking old and current address",
    "DOC_BANK_DETAILS_CLAIMANT": "Claimant's bank account details (cancelled cheque)",
    "DOC_PAN_DECEASED": "PAN of the deceased",
    "DOC_RELATIONSHIP_PROOF": "Proof of the claimant's relationship to the deceased",
}


def is_valid(code: str) -> bool:
    return code in DOC_CODES
