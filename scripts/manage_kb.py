"""
Management CLI for the DidI Knowledge Base.
Allows manual mapping of people, organizations, and aliases.
"""
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.knowledge_base import KnowledgeBase

def main():
    parser = argparse.ArgumentParser(description="Manage DidI Knowledge Base (Identities & Orgs)")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add Entity
    add_ep = subparsers.add_parser("add-entity", help="Add a new person or organization")
    add_ep.add_argument("name", help="Canonical name (e.g., 'Alice Smith')")
    add_ep.add_argument("--type", choices=['person', 'organization', 'group'], default='person')
    add_ep.add_argument("--dept", help="Department")
    add_ep.add_argument("--role", help="Role")

    # Add Alias
    add_al = subparsers.add_parser("add-alias", help="Map an email/handle to an entity")
    add_al.add_argument("entity_id", help="UUID of the entity")
    add_al.add_argument("value", help="Email, Slack ID, or handle")
    add_al.add_argument("--type", choices=['email', 'slack_id', 'handle'], default='email')

    # Link Org
    link_org = subparsers.add_parser("link-org", help="Link a person to an organization")
    link_org.add_argument("person_id", help="UUID of the person")
    link_org.add_argument("org_id", help="UUID of the organization")

    # List
    list_e = subparsers.add_parser("list", help="List entities")
    list_e.add_argument("--type", choices=['person', 'organization', 'group'])

    args = parser.parse_args()
    
    kb = KnowledgeBase()

    if args.command == "add-entity":
        metadata = {}
        if args.dept: metadata['dept'] = args.dept
        if args.role: metadata['role'] = args.role
        
        eid = kb.add_entity(args.name, args.type, metadata)
        print(f"[OK] Added {args.type}: {args.name}")
        print(f"     ID: {eid}")

    elif args.command == "add-alias":
        kb.add_alias(args.entity_id, args.value, args.type)
        print(f"[OK] Mapped {args.type} '{args.value}' to entity {args.entity_id}")

    elif args.command == "link-org":
        kb.link_to_org(args.person_id, args.org_id)
        print(f"[OK] Linked person {args.person_id} to organization {args.org_id}")

    elif args.command == "list":
        entities = kb.get_all_entities(args.type)
        print(f"\n{'ID':<38} | {'Type':<12} | {'Name'}")
        print("-" * 70)
        for e in entities:
            print(f"{e['id']:<38} | {e['type']:<12} | {e['canonical_name']}")
        print()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
