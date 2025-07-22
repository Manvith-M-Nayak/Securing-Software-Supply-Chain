# Commit model for MongoDB

def commit_doc(commit_id, project_name, message, author, author_email, timestamp, url, is_on_blockchain=False, blockchain_tx_hash=None, status="pending", audit_status=None):
    return {
        "id": commit_id,
        "projectName": project_name,
        "message": message,
        "author": author,
        "authorEmail": author_email,
        "timestamp": timestamp,
        "url": url,
        "isOnBlockchain": is_on_blockchain,
        "blockchainTxHash": blockchain_tx_hash,
        "status": status,  # pending, accepted, rejected
        "auditStatus": audit_status,  # accepted, rejected, pending
        "createdAt": timestamp,
    } 