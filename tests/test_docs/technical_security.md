# Network Security: Protocols, Vulnerabilities, and Hardening

## Encryption Standards

### AES (Advanced Encryption Standard)
AES was adopted by NIST on November 26, 2001 as FIPS-197, replacing the older DES standard. The algorithm was originally called Rijndael, designed by Joan Daemen and Vincent Rijmen from Belgium. AES supports three key sizes: 128-bit (10 rounds), 192-bit (12 rounds), and 256-bit (14 rounds). AES-256 is used by the U.S. government for TOP SECRET classified information.

The theoretical time to brute-force AES-256 is 3.31 x 10^56 years using current computing power. In comparison, DES with its 56-bit key can be cracked in under 24 hours using modern hardware.

### TLS 1.3
TLS 1.3 was published as RFC 8446 on August 10, 2018. Major improvements over TLS 1.2 include: the handshake was reduced from 2 round trips to 1 round trip (1-RTT), and a 0-RTT resumption mode was added for returning connections. TLS 1.3 removed support for RSA key transport, static Diffie-Hellman, custom DHE groups, compression, and RC4. The only cipher suites allowed in TLS 1.3 are based on AEAD algorithms: AES-128-GCM, AES-256-GCM, and CHACHA20-POLY1305.

## Common Vulnerabilities

### SQL Injection (CWE-89)
SQL injection has been ranked as the #1 web application vulnerability by OWASP from 2010 to 2017. In 2021, it was reclassified under A03:2021 Injection category. The largest known SQL injection breach was the Heartland Payment Systems attack in 2008, which exposed 134 million credit card numbers. Prevention methods include parameterized queries, stored procedures, input validation, and WAF (Web Application Firewall) rules.

### Buffer Overflow (CWE-120)
The Morris Worm of November 2, 1988 was the first major buffer overflow exploit on the internet, infecting approximately 6,000 computers (10% of the internet at that time). Modern prevention techniques include ASLR (Address Space Layout Randomization), stack canaries, DEP (Data Execution Prevention), and Control Flow Integrity (CFI). The average cost of a buffer overflow vulnerability in critical infrastructure is estimated at $4.35 million per incident according to IBM's 2022 Cost of a Data Breach Report.

### Log4Shell (CVE-2021-44228)
Discovered on December 9, 2021, Log4Shell affected Apache Log4j versions 2.0-beta9 through 2.14.1. It received a CVSS score of 10.0 (the maximum). The vulnerability allowed Remote Code Execution (RCE) through JNDI lookup injection. Over 35,863 Java packages (approximately 8% of Maven Central) were affected. The fix was released in Log4j version 2.15.0, with additional patches in 2.16.0 and 2.17.0.

## Network Hardening Checklist

### Firewall Configuration
A properly configured perimeter firewall should implement the following rules:
1. Default deny all inbound traffic
2. Allow only necessary ports (e.g., 443 for HTTPS, 22 for SSH)
3. Enable stateful packet inspection
4. Rate limit connections to 100 per second per source IP
5. Block RFC 1918 private addresses on public interfaces (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
6. Enable logging for all denied packets
7. Review rules quarterly at minimum

### Password Policy (NIST SP 800-63B)
NIST Special Publication 800-63B recommends: minimum 8 characters for user-chosen passwords, minimum 6 characters for randomly generated passwords, maximum length of at least 64 characters, no composition rules (no forced uppercase/number/symbol requirements), and checking against a list of at least 100,000 commonly used passwords. Password rotation should NOT be required unless there is evidence of compromise.
