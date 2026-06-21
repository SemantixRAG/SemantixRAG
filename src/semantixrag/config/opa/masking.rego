package semantix.masking

# Default: mask all PII
default mask = true

# Never mask for admin compliance officers
mask = false {
    input.user_role == "admin"
}

mask = false {
    input.user_role == "compliance_officer"
    input.reason == "audit"
}

# Mask specific PII types based on user role
mask_by_type[pii_type] {
    input.user_role == "viewer"
    pii_type := input.pii_types[_]
}

mask_by_type[pii_type] {
    input.user_role == "data_scientist"
    input.pii_types[_] == "SSN"
    pii_type := "SSN"
}

# Different masking strategies per user
mask_strategy = "type_specific" {
    input.user_role == "viewer"
}

mask_strategy = "none" {
    input.user_role == "admin"
}

mask_strategy = "uniform" {
    input.user_role == "external_auditor"
}